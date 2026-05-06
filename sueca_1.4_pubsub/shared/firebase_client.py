import os
import json
import hashlib
from pathlib import Path
from typing import Optional
import datetime
import secrets

import firebase_admin
from firebase_admin import credentials, firestore

_APP = None
_DB = None


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _read_key_from_env_file(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "FIREBASE_SERVICE_ACCOUNT_KEY":
            return value.strip().strip('"').strip("'")
    return None


def _resolve_service_account_key() -> str:
    key_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    if key_str:
        return key_str

    project_root = Path(__file__).resolve().parents[1]
    candidates = [
        project_root / ".env",
        project_root / "apps" / "twilio" / ".env",
        project_root / "apps" / "auth" / "twilio" / ".env",
        project_root / "apps" / "auth" / "friends" / ".env",
        project_root / "apps" / "auth" / ".env",
    ]
    for candidate in candidates:
        value = _read_key_from_env_file(candidate)
        if value:
            os.environ["FIREBASE_SERVICE_ACCOUNT_KEY"] = value
            return value

    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_KEY is not set")


def _ensure_app():
    global _APP, _DB
    if _APP and _DB:
        return

    key_str = _resolve_service_account_key()

    key_dict = json.loads(key_str)
    cred = credentials.Certificate(key_dict)
    if not firebase_admin._apps:
        _APP = firebase_admin.initialize_app(cred)
    _DB = firestore.client()


def get_user(uid: str) -> Optional[dict]:
    _ensure_app()
    doc = _DB.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_user(uid: str, data: dict):
    _ensure_app()
    _DB.collection("users").document(uid).set(data)


def delete_user(uid: str):
    _ensure_app()
    _DB.collection("users").document(uid).delete()


def find_users_by_username(username: str) -> list[dict]:
    _ensure_app()
    docs = _DB.collection("users").where("username", "==", username).stream()
    out = []
    for d in docs:
        data = d.to_dict() or {}
        data["uid"] = d.id
        out.append(data)
    return out


def find_user_by_email(email: str) -> Optional[dict]:
    _ensure_app()
    docs = list(_DB.collection("users").where("email", "==", email).limit(1).stream())
    if not docs:
        return None
    data = docs[0].to_dict() or {}
    data["uid"] = docs[0].id
    return data


def find_user_by_friend_code(friend_code: str) -> Optional[dict]:
    _ensure_app()
    docs = list(_DB.collection("users").where("friendCode", "==", friend_code).limit(1).stream())
    if not docs:
        return None
    data = docs[0].to_dict() or {}
    data["uid"] = docs[0].id
    return data


def generate_unique_friend_code() -> str:
    _ensure_app()
    for _ in range(20):
        code = f"{secrets.randbelow(100_000_000):08d}"
        if not find_user_by_friend_code(code):
            return code
    # Extremely unlikely fallback.
    return f"{secrets.randbelow(100_000_000):08d}"


def set_verification(username: str, code: str, kind: str = "register", ttl_seconds: int = 600):
    _ensure_app()
    salt = secrets.token_hex(16)
    code_hash = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    expires = _utc_now() + datetime.timedelta(seconds=ttl_seconds)
    _DB.collection("verifications").document(username).set({
        "code_hash": code_hash,
        "salt": salt,
        "kind": kind,
        "expires_at": expires,
    })


def check_verification(username: str, code: str, kind: str = "register") -> bool:
    _ensure_app()
    doc = _DB.collection("verifications").document(username).get()
    if not doc.exists:
        return False
    data = doc.to_dict()
    if data.get("kind") != kind:
        return False
    salt = data.get("salt")
    code_hash = data.get("code_hash")
    if not salt or not code_hash:
        return False
    candidate_hash = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    if not secrets.compare_digest(code_hash, candidate_hash):
        return False
    expires = data.get("expires_at")
    if expires and isinstance(expires, datetime.datetime):
        if expires < _utc_now():
            return False
    # delete after successful
    _DB.collection("verifications").document(username).delete()
    return True


def add_friend(user: str, friend: str):
    _ensure_app()
    doc_ref = _DB.collection("friends").document(user)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        arr = data.get("friends", [])
        if friend in arr:
            return False
        arr.append(friend)
        doc_ref.set({"friends": arr})
    else:
        doc_ref.set({"friends": [friend]})
    return True


def get_friends(user: str) -> list:
    _ensure_app()
    doc = _DB.collection("friends").document(user).get()
    if not doc.exists:
        return []
    return doc.to_dict().get("friends", [])


def remove_friend(user: str, friend: str) -> bool:
    _ensure_app()
    doc_ref = _DB.collection("friends").document(user)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    arr = doc.to_dict().get("friends", [])
    if friend not in arr:
        return False
    arr.remove(friend)
    doc_ref.set({"friends": arr})
    return True


def revoke_token(jti: str):
    _ensure_app()
    _DB.collection("revoked_tokens").document(jti).set({"revoked": True})


def is_token_revoked(jti: str) -> bool:
    _ensure_app()
    doc = _DB.collection("revoked_tokens").document(jti).get()
    return doc.exists


# Friend request workflow
def add_friend_request(from_user: str, to_user: str) -> bool:
    _ensure_app()
    doc_id = f"{to_user}:{from_user}"
    doc_ref = _DB.collection("friend_requests").document(doc_id)
    if doc_ref.get().exists:
        return False
    doc_ref.set({
        "from": from_user,
        "to": to_user,
        "created_at": _utc_now(),
    })
    return True


def get_incoming_friend_requests(user: str) -> list:
    _ensure_app()
    docs = _DB.collection("friend_requests").where("to", "==", user).stream()
    out = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        out.append(data)
    return out


def accept_friend_request(user: str, from_user: str) -> bool:
    _ensure_app()
    # Add mutual friendship
    add_friend(user, from_user)
    add_friend(from_user, user)
    # remove request
    doc_id = f"{user}:{from_user}"
    _DB.collection("friend_requests").document(doc_id).delete()
    return True


def reject_friend_request(user: str, from_user: str) -> bool:
    _ensure_app()
    doc_id = f"{user}:{from_user}"
    doc_ref = _DB.collection("friend_requests").document(doc_id)
    if not doc_ref.get().exists:
        return False
    doc_ref.delete()
    return True
