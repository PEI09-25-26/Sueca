from datetime import datetime, timedelta
import os
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
import jwt

from apps.virtual_engine.session import decode_session_token
from shared.auth import decode_access_token, extract_bearer_token
from shared.ratelimit import rate_limit_dependency

router = APIRouter()


class GameTokenRequest(BaseModel):
    game_id: str


class GameTokenResponse(BaseModel):
    token: str
    expires_at: str


@router.post(
    "/auth/game_token",
    response_model=GameTokenResponse,
    dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))],
)
def issue_game_token(req: GameTokenRequest, authorization: str | None = Header(default=None)):
    """Issue a short-lived JWT for a given game_id to an authenticated player session."""
    token = extract_bearer_token(authorization)

    session_payload = None
    try:
        session_payload = decode_session_token(token)
    except jwt.InvalidTokenError:
        try:
            decode_access_token(token)
        except HTTPException as error:
            raise HTTPException(status_code=401, detail="invalid token") from error

    if session_payload and session_payload.get("game_id") != req.game_id:
        raise HTTPException(status_code=403, detail="forbidden")

    secret = os.getenv("SUECA_JWT_SECRET", "dev-secret")
    ttl = int(os.getenv("SUECA_GAME_TOKEN_TTL", "300"))  # seconds
    now = datetime.utcnow()
    exp = now + timedelta(seconds=ttl)
    payload = {"game_id": req.game_id, "exp": int(exp.timestamp())}
    token = jwt.encode(payload, secret, algorithm="HS256")
    return GameTokenResponse(token=token, expires_at=exp.isoformat() + "Z")
