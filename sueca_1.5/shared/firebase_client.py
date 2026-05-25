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


def _to_iso(value) -> str:
    if isinstance(value, datetime.datetime):
        return value.astimezone(datetime.timezone.utc).isoformat()
    if value is None:
        return _utc_now().isoformat()
    return str(value)


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


def get_player_stats(player_id: str) -> Optional[dict]:
    """Fetch player stats by friend code (player_id), supporting both doc-id and field lookup."""
    _ensure_app()
    normalized_id = (player_id or "").strip()
    if not normalized_id:
        return None

    # Preferred lookup: document id equals player_id/friendCode.
    doc = _DB.collection("player_stats").document(normalized_id).get()
    if doc.exists:
        data = doc.to_dict() or {}
        data.setdefault("player_id", normalized_id)
        return data

    # Fallback lookup: player_id stored as a field in an arbitrary document id.
    docs = list(_DB.collection("player_stats").where("player_id", "==", normalized_id).limit(1).stream())
    if not docs:
        return None

    data = docs[0].to_dict() or {}
    data.setdefault("player_id", normalized_id)
    return data


def generate_unique_friend_code() -> str:
    _ensure_app()
    for _ in range(20):
        code = f"{secrets.randbelow(100_000_000):08d}"
        if not find_user_by_friend_code(code):
            return code
    # Extremely unlikely fallback.
    return f"{secrets.randbelow(100_000_000):08d}"


def set_verification(
    verification_id: str,
    code: str,
    kind: str = "register",
    ttl_seconds: int = 600,
    *,
    subject: str | None = None,
    max_attempts: int = 5,
):
    _ensure_app()
    salt = secrets.token_hex(16)
    code_hash = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    expires = _utc_now() + datetime.timedelta(seconds=ttl_seconds)
    _DB.collection("verifications").document(verification_id).set({
        "code_hash": code_hash,
        "salt": salt,
        "kind": kind,
        "expires_at": expires,
        "subject": subject or verification_id,
        "failed_attempts": 0,
        "max_attempts": max(1, int(max_attempts)),
    })


def check_verification(username: str, code: str, kind: str = "register") -> bool:
    return consume_verification(username, code, kind=kind) is not None


def consume_verification(verification_id: str, code: str, kind: str = "register") -> Optional[str]:
    _ensure_app()
    doc_ref = _DB.collection("verifications").document(verification_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if data.get("kind") != kind:
        return None
    salt = data.get("salt")
    code_hash = data.get("code_hash")
    if not salt or not code_hash:
        return None
    failed_attempts = int(data.get("failed_attempts", 0))
    max_attempts = max(1, int(data.get("max_attempts", 5)))
    if failed_attempts >= max_attempts:
        return None
    candidate_hash = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    if not secrets.compare_digest(code_hash, candidate_hash):
        doc_ref.set({"failed_attempts": failed_attempts + 1}, merge=True)
        return None
    expires = data.get("expires_at")
    if expires and isinstance(expires, datetime.datetime):
        if expires < _utc_now():
            return None
    # delete after successful
    doc_ref.delete()
    return str(data.get("subject") or verification_id)


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
    now = _utc_now()
    from_user_doc = get_user(from_user) or {}
    doc_ref.set({
        "from_uid": from_user,
        "to_uid": to_user,
        "from_username": from_user_doc.get("username", ""),
        "status": "pending",
        "createdAt": now,
        "updatedAt": now,
    })
    return True


def get_incoming_friend_requests(user: str) -> list:
    _ensure_app()
    out = []
    docs = _DB.collection("friend_requests").stream()
    for d in docs:
        data = d.to_dict()
        to_uid = data.get("to_uid") or data.get("to") or ""
        if to_uid != user:
            continue

        from_uid = data.get("from_uid") or data.get("from") or ""
        from_user_doc = get_user(from_uid) if from_uid else None
        data["id"] = d.id
        data["from_uid"] = from_uid
        data["to_uid"] = to_uid
        data["from_username"] = data.get("from_username") or (from_user_doc.get("username", "") if from_user_doc else "")
        data["status"] = data.get("status") or "pending"
        data["createdAt"] = _to_iso(data.get("createdAt") or data.get("created_at"))
        data["updatedAt"] = _to_iso(data.get("updatedAt") or data.get("updated_at") or data.get("createdAt"))
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

def get_firestore_db():
    _ensure_app()
    return _DB