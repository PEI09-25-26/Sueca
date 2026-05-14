from datetime import datetime, timedelta
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt

router = APIRouter()


class GameTokenRequest(BaseModel):
    game_id: str


class GameTokenResponse(BaseModel):
    token: str
    expires_at: str


@router.post("/auth/game_token", response_model=GameTokenResponse)
def issue_game_token(req: GameTokenRequest):
    """Issue a short-lived JWT for a given game_id. In production validate requester permissions."""
    secret = os.getenv("SUECA_JWT_SECRET", "dev-secret")
    ttl = int(os.getenv("SUECA_GAME_TOKEN_TTL", "300"))  # seconds
    now = datetime.utcnow()
    exp = now + timedelta(seconds=ttl)
    payload = {"game_id": req.game_id, "exp": int(exp.timestamp())}
    token = jwt.encode(payload, secret, algorithm="HS256")
    return GameTokenResponse(token=token, expires_at=exp.isoformat() + "Z")
