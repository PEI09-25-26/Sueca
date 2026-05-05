import datetime
import os
import secrets
import uuid

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from passlib.hash import bcrypt_sha256
from pydantic import BaseModel, Field

from apps.auth.twilio.email_service import EmailService
from shared.firebase_client import (
    check_verification,
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

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))

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
    code: str


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


@app.get("/health")
def health():
    return {"healthy": True}


@app.post("/register", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def register(req: RegisterRequest):
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

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

    verification_id = uid
    if email:
        code = f"{secrets.randbelow(1000000):06d}"
        set_verification(verification_id, code, kind="register", ttl_seconds=600)
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
    ok = check_verification(req.verification_id, req.code, kind="register")
    if not ok:
        raise HTTPException(status_code=400, detail="invalid or expired code")

    uid = req.verification_id
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
def get_user_endpoint(uid: str):
    user = get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return {"success": True, "user": _build_user_response(uid, user)}


@app.get("/user/by-friend-code/{friend_code}", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_user_by_friend_code(friend_code: str) -> FriendCodeLookupResponse:
    user_with_uid = find_user_by_friend_code(friend_code)
    if not user_with_uid:
        raise HTTPException(status_code=404, detail="user not found")
    uid = user_with_uid.get("uid")
    user = get_user(uid) if uid else None
    if not uid or not user:
        raise HTTPException(status_code=404, detail="user not found")
    return FriendCodeLookupResponse(success=True, user=_build_user_response(uid, user))


@app.put("/user/{uid}", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def update_user_endpoint(uid: str, req: UpdateUserRequest):
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
def logout(req: LogoutRequest, authorization: str | None = Header(default=None)):
    token = req.token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        return {"success": True}

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    jti = payload.get("jti")
    if jti:
        revoke_token(jti)
    return {"success": True}


@app.post("/request-delete", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def request_delete(req: DeleteRequest):
    user = get_user(req.uid)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    email = (user.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="email required for delete verification")

    code = f"{secrets.randbelow(1000000):06d}"
    set_verification(req.uid, code, kind="delete", ttl_seconds=600)
    try:
        EmailService().send_verification_code(email, code, user.get("username", "user"))
    except Exception:
        pass
    return {"success": True}


@app.post("/confirm-delete", dependencies=[Depends(rate_limit_dependency(limit=5, window_seconds=60))])
def confirm_delete(req: ConfirmDeleteRequest):
    ok = check_verification(req.uid, req.code, kind="delete")
    if not ok:
        raise HTTPException(status_code=400, detail="invalid or expired code")

    delete_user(req.uid)
    return {"success": True}
