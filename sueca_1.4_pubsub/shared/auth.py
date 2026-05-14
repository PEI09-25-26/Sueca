import os

import jwt
from fastapi import Header, HTTPException, status

from shared.firebase_client import is_token_revoked


JWT_ALGORITHM = "HS256"


def _secret_key() -> str:
    return os.getenv("SECRET_KEY", "dev-secret")


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid authorization header",
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return token


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        ) from error

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token revoked",
        )
    return payload


def get_authenticated_payload(authorization: str | None = Header(default=None)) -> dict:
    token = extract_bearer_token(authorization)
    return decode_access_token(token)


def get_authenticated_uid(authorization: str | None = Header(default=None)) -> str:
    payload = get_authenticated_payload(authorization)
    uid = payload.get("uid") or payload.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token missing subject",
        )
    return str(uid)
