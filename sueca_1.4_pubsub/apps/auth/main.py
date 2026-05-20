import datetime
import os
import secrets
import uuid

import jwt
from fastapi import Depends, FastAPI, HTTPException, Header, status
from passlib.hash import bcrypt_sha256
from pydantic import BaseModel, Field
from shared.logging_config import setup_logging, correlation_id_from_request, set_correlation_id, clear_correlation_id

setup_logging()

from apps.auth.twilio.email_service import EmailService
from shared.auth import get_authenticated_payload, get_authenticated_uid
from shared.firebase_client import (
    consume_verification,
    create_user,
    delete_user,
    find_user_by_email,
    find_user_by_friend_code,
    find_users_by_username,
    generate_unique_friend_code,
    get_user,
    revoke_token,
    set_verification,
)
from shared.ratelimit import rate_limit_dependency

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in environment")

SUECA_SERVICE_JWT_SECRET = os.getenv("SUECA_SERVICE_JWT_SECRET")
if not SUECA_SERVICE_JWT_SECRET:
    raise RuntimeError("SUECA_SERVICE_JWT_SECRET must be set in environment")

JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
SERVICE_TOKEN_EXP_SECONDS = int(os.getenv("SERVICE_TOKEN_EXP_SECONDS", "900"))  # 15 minutes

app = FastAPI(title="Sueca Auth Service")


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class VerifyRequest(BaseModel):
    verification_id: str = Field(alias="verification_id")
    code: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutRequest(BaseModel):
    token: str | None = None
    uid: str | None = None


class UpdateUserRequest(BaseModel):
    description: str | None = None
    photoURL: str | None = None
    bannerURL: str | None = None
    privacy: str | None = None
    status: str | None = None


class DeleteRequest(BaseModel):
    uid: str


class ConfirmDeleteRequest(BaseModel):
    uid: str
    verification_id: str = Field(alias="verification_id")
    code: str


class ResetPasswordRequest(BaseModel):
    verification_id: str = Field(alias="verification_id")
    code: str
    new_password: str


class ValidateTokenRequest(BaseModel):
    token: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    payload: dict | None = None
    error: str | None = None


class ServiceTokenRequest(BaseModel):
    service_name: str
    scope: str


class ServiceTokenResponse(BaseModel):
    success: bool
    token: str
    expires_in: int


class FriendCodeLookupResponse(BaseModel):
    success: bool
    user: dict | None = None


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _isoformat(value: datetime.datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return _isoformat(_utc_now()) or ""


def _issue_jwt(uid: str) -> str:
    jti = str(uuid.uuid4())
    now = _utc_now()
    payload = {
        "sub": uid,
        "uid": uid,
        "iat": now,
        "exp": now + datetime.timedelta(seconds=JWT_EXP_SECONDS),
        "jti": jti,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def _issue_service_token(service_name: str, scope: str) -> str:
    """Issue a short-lived service-to-service token."""
    jti = str(uuid.uuid4())
    now = _utc_now()
    payload = {
        "service": service_name,
        "scope": scope,
        "iat": now,
        "exp": now + datetime.timedelta(seconds=SERVICE_TOKEN_EXP_SECONDS),
        "jti": jti,
        "type": "service",
    }
    return jwt.encode(payload, SUECA_SERVICE_JWT_SECRET, algorithm=JWT_ALGORITHM)


def _build_user_response(uid: str, user: dict, *, last_login_at: str | None = None) -> dict:
    created_at = user.get("createdAt") or _now_iso()
    updated_at = user.get("updatedAt") or created_at
    return {
        "uid": uid,
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "emailVerified": bool(user.get("verified", False)),
        "description": user.get("description", ""),
        "photoURL": user.get("photoURL", ""),
        "bannerURL": user.get("bannerURL", ""),
        "createdAt": created_at,
        "updatedAt": updated_at,
        "lastLoginAt": last_login_at,
        "privacy": user.get("privacy", "public"),
        "friendsCount": int(user.get("friendsCount", 0)),
        "status": user.get("status", "offline"),
        "friendCode": user.get("friendCode", ""),
    }


def _build_public_user_response(uid: str, user: dict) -> dict:
    return {
        "uid": uid,
        "username": user.get("username", ""),
        "email": "",
        "emailVerified": bool(user.get("verified", False)),
        "description": user.get("description", ""),
        "photoURL": user.get("photoURL", ""),
        "bannerURL": user.get("bannerURL", ""),
        "createdAt": user.get("createdAt") or _now_iso(),
        "updatedAt": user.get("updatedAt") or user.get("createdAt") or _now_iso(),
        "lastLoginAt": None,
        "privacy": user.get("privacy", "public"),
        "friendsCount": int(user.get("friendsCount", 0)),
        "status": user.get("status", "offline"),
        "friendCode": user.get("friendCode", ""),
    }


def _ensure_password_strength(password: str):
    if len(password or "") < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")


def _ensure_same_user(requested_uid: str, authenticated_uid: str):
    if requested_uid != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")


def _pick_login_user(identifier: str, password: str) -> tuple[str, dict] | None:
    identifier = identifier.strip()
    if "@" in identifier:
        by_email = find_user_by_email(identifier)
        if not by_email:
            return None
        uid = by_email.get("uid")
        if not uid:
            return None
        user = get_user(uid)
        if not user:
            return None
        salted = f"{user.get('salt', '')}{password}"
        if bcrypt_sha256.verify(salted, user.get("password", "")):
            return uid, user
        return None

    candidates = find_users_by_username(identifier)
    for candidate in candidates:
        uid = candidate.get("uid")
        if not uid:
            continue
        user = get_user(uid)
        if not user:
            continue
        salted = f"{user.get('salt', '')}{password}"
        try:
            if bcrypt_sha256.verify(salted, user.get("password", "")):
                return uid, user
        except Exception:
            continue
    return None


# Correlation-id middleware must be registered after `app` is defined
from fastapi import Request


@app.middleware("http")
async def _add_cid(request: Request, call_next):
    cid = correlation_id_from_request(request)
    request.state.correlation_id = cid
    set_correlation_id(cid)
    try:
        resp = await call_next(request)
        resp.headers['X-Correlation-ID'] = cid
        return resp
    finally:
        clear_correlation_id()


def require_control_plane_token(authorization: str | None = Header(default=None)) -> bool:
    """Dependency that enforces a signed service JWT for control-plane actions."""
    if not SUECA_SERVICE_JWT_SECRET:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="server misconfigured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid authorization header")

    token = authorization[7:].strip()
    try:
        payload = jwt.decode(token, SUECA_SERVICE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service token")

    if payload.get("scope") != "control_plane":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient scope")

    return True


@app.get("/health")
def health():
    return {"healthy": True}


@app.post("/register", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def register(req: RegisterRequest):
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    _ensure_password_strength(req.password)

    email = (req.email or "").strip().lower()
    if email:
        if find_user_by_email(email):
            raise HTTPException(status_code=400, detail="email already in use")

    uid = uuid.uuid4().hex
    salt = secrets.token_hex(16)
    salted = f"{salt}{req.password}"
    pw_hash = bcrypt_sha256.hash(salted)
    created_at = _now_iso()
    friend_code = generate_unique_friend_code()

    user_doc = {
        "username": username,
        "email": email,
        "salt": salt,
        "password": pw_hash,
        "verified": False,
        "createdAt": created_at,
        "updatedAt": created_at,
        "privacy": "public",
        "friendsCount": 0,
        "status": "offline",
        "description": "",
        "photoURL": "",
        "bannerURL": "",
        "friendCode": friend_code,
    }
    create_user(uid, user_doc)

    verification_id = uuid.uuid4().hex
    if email:
        code = f"{secrets.randbelow(1000000):06d}"
        set_verification(verification_id, code, kind="register", ttl_seconds=600, subject=uid, max_attempts=5)
        try:
            EmailService().send_verification_code(email, code, username)
        except Exception:
            pass

    return {
        "success": True,
        "uid": uid,
        "username": username,
        "friendCode": friend_code,
        "message": "verification required" if email else "registered",
        "verificationRequired": bool(email),
        "verificationId": verification_id if email else None,
    }


@app.post("/verify-register", dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))])
@app.post("/verify-email", dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))])
def verify_register(req: VerifyRequest):
    uid = consume_verification(req.verification_id, req.code, kind="register")
    if not uid:
        raise HTTPException(status_code=400, detail="invalid or expired code")
    user = get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="not found")

    user["verified"] = True
    user["updatedAt"] = _now_iso()
    create_user(uid, user)
    token = _issue_jwt(uid)
    return {
        "success": True,
        "message": "Email verified",
        "user": _build_user_response(uid, user, last_login_at=_now_iso()),
        "token": token,
    }


@app.post("/login", dependencies=[Depends(rate_limit_dependency(limit=6, window_seconds=60))])
def login(req: LoginRequest):
    picked = _pick_login_user(req.username, req.password)
    if not picked:
        raise HTTPException(status_code=401, detail="invalid credentials")

    uid, user = picked
    token = _issue_jwt(uid)
    user["updatedAt"] = _now_iso()
    create_user(uid, user)
    return {
        "success": True,
        "message": "Login successful",
        "user": _build_user_response(uid, user, last_login_at=_now_iso()),
        "token": token,
    }


@app.get("/user/{uid}", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_user_endpoint(uid: str, authenticated_uid: str = Depends(get_authenticated_uid)):
    _ensure_same_user(uid, authenticated_uid)
    user = get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return {"success": True, "user": _build_user_response(uid, user)}


@app.get("/user/by-friend-code/{friend_code}", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_user_by_friend_code(friend_code: str, _: str = Depends(get_authenticated_uid)) -> FriendCodeLookupResponse:
    user_with_uid = find_user_by_friend_code(friend_code)
    if not user_with_uid:
        raise HTTPException(status_code=404, detail="user not found")
    uid = user_with_uid.get("uid")
    user = get_user(uid) if uid else None
    if not uid or not user:
        raise HTTPException(status_code=404, detail="user not found")
    return FriendCodeLookupResponse(success=True, user=_build_public_user_response(uid, user))


@app.put("/user/{uid}", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def update_user_endpoint(uid: str, req: UpdateUserRequest, authenticated_uid: str = Depends(get_authenticated_uid)):
    _ensure_same_user(uid, authenticated_uid)
    user = get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if req.description is not None:
        user["description"] = req.description
    if req.photoURL is not None:
        user["photoURL"] = req.photoURL
    if req.bannerURL is not None:
        user["bannerURL"] = req.bannerURL
    if req.privacy is not None:
        user["privacy"] = req.privacy
    if req.status is not None:
        user["status"] = req.status

    user["updatedAt"] = _now_iso()
    create_user(uid, user)
    return {"success": True, "user": _build_user_response(uid, user)}


@app.post("/logout", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def logout(req: LogoutRequest, auth_payload: dict = Depends(get_authenticated_payload)):
    if req.uid:
        _ensure_same_user(req.uid, str(auth_payload.get("uid") or auth_payload.get("sub") or ""))
    jti = auth_payload.get("jti")
    if jti:
        revoke_token(jti)
    return {"success": True}


@app.post("/request-delete", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def request_delete(req: DeleteRequest, authenticated_uid: str = Depends(get_authenticated_uid)):
    _ensure_same_user(req.uid, authenticated_uid)
    user = get_user(authenticated_uid)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    email = (user.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="email required for delete verification")

    code = f"{secrets.randbelow(1000000):06d}"
    verification_id = uuid.uuid4().hex
    set_verification(verification_id, code, kind="delete", ttl_seconds=600, subject=authenticated_uid, max_attempts=5)
    try:
        EmailService().send_verification_code(email, code, user.get("username", "user"))
    except Exception:
        pass
    return {"success": True, "verificationId": verification_id}


@app.post("/confirm-delete", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def confirm_delete(req: ConfirmDeleteRequest, authenticated_uid: str = Depends(get_authenticated_uid)):
    _ensure_same_user(req.uid, authenticated_uid)
    verified_uid = consume_verification(req.verification_id, req.code, kind="delete")
    if not verified_uid:
        raise HTTPException(status_code=400, detail="invalid or expired code")
    _ensure_same_user(verified_uid, authenticated_uid)

    delete_user(authenticated_uid)
    return {"success": True}

@app.get("/recover-password", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def recover_password(email: str):
    email = email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")

    user = find_user_by_email(email)
    verification_id = uuid.uuid4().hex

    if user:
        uid = user.get("uid")
        if uid:
            code = f"{secrets.randbelow(1000000):06d}"
            set_verification(verification_id, code, kind="recover", ttl_seconds=600, subject=uid, max_attempts=5)
            try:
                EmailService().send_password_recovery_code(email, code, user.get("username", "user"))
            except Exception:
                pass

    return {
        "success": True,
        "verificationId": verification_id,
        "message": "If the account exists, a recovery code has been sent",
    }

@app.post("/reset-password", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def reset_password(req: ResetPasswordRequest):
    verified_uid = consume_verification(req.verification_id, req.code, kind="recover")
    if not verified_uid:
        raise HTTPException(status_code=400, detail="invalid or expired code")

    user = get_user(verified_uid)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    new_password = req.new_password.strip()
    if not new_password:
        raise HTTPException(status_code=400, detail="new password required")
    _ensure_password_strength(new_password)

    salt = secrets.token_hex(16)
    salted = f"{salt}{new_password}"
    user["salt"] = salt
    user["password"] = bcrypt_sha256.hash(salted)
    user["updatedAt"] = _now_iso()
    create_user(verified_uid, user)

    return {"success": True, "message": "Password updated"}


# ============================================================
# CENTRALIZED TOKEN VALIDATION ENDPOINTS
# ============================================================

class UpdateUserStatusRequest(BaseModel):
    uid: str
    status: str


@app.put("/user/{uid}/status", dependencies=[Depends(require_control_plane_token)])
def update_user_status_internal(uid: str, req: UpdateUserStatusRequest):
    user = get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    user["status"] = req.status
    user["updatedAt"] = _now_iso()
    create_user(uid, user)
    return {"success": True, "status": req.status}


@app.post("/validate/token", dependencies=[Depends(rate_limit_dependency(limit=100, window_seconds=60))])
def validate_token_endpoint(req: ValidateTokenRequest) -> ValidateTokenResponse:
    """Centralized token validation for all services."""
    from shared.auth import decode_access_token

    try:
        payload = decode_access_token(req.token)
        return ValidateTokenResponse(valid=True, payload=payload)
    except HTTPException as e:
        return ValidateTokenResponse(valid=False, error=e.detail)
    except Exception:
        return ValidateTokenResponse(valid=False, error="token validation failed")


@app.post("/validate/service", dependencies=[Depends(rate_limit_dependency(limit=100, window_seconds=60))])
def validate_service_token_endpoint(req: ValidateTokenRequest) -> ValidateTokenResponse:
    """Validate service-to-service tokens."""
    try:
        payload = jwt.decode(req.token, SUECA_SERVICE_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Ensure it's a service token
        if payload.get("type") != "service":
            return ValidateTokenResponse(valid=False, error="not a service token")
        
        # Check JTI denylist
        jti = payload.get("jti")
        if jti:
            from shared.redis_client import is_jti_revoked
            if is_jti_revoked(jti):
                return ValidateTokenResponse(valid=False, error="token revoked")
        
        return ValidateTokenResponse(valid=True, payload=payload)
    except jwt.ExpiredSignatureError:
        return ValidateTokenResponse(valid=False, error="token expired")
    except jwt.InvalidTokenError:
        return ValidateTokenResponse(valid=False, error="invalid token")
    except Exception:
        return ValidateTokenResponse(valid=False, error="token validation failed")


# ============================================================
# SERVICE TOKEN ISSUANCE ENDPOINTS
# ============================================================

@app.post("/service-token/issue", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def issue_service_token(req: ServiceTokenRequest) -> ServiceTokenResponse:
    """Issue a short-lived service-to-service token.
    
    Service tokens are used for control-plane operations and should be:
    - Short-lived (15 minutes by default)
    - Scoped (e.g., 'control_plane')
    - Issued only to trusted services
    
    In production, this endpoint should be protected (e.g., by mTLS or static service secret).
    """
    if not req.service_name or not req.scope:
        raise HTTPException(status_code=400, detail="service_name and scope required")
    
    token = _issue_service_token(req.service_name, req.scope)
    return ServiceTokenResponse(
        success=True,
        token=token,
        expires_in=SERVICE_TOKEN_EXP_SECONDS,
    )

