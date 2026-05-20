from datetime import datetime, timedelta
import os
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
import jwt

import logging

from apps.virtual_engine.session import session_manager
from ..helpers import require_any_token
from shared.ratelimit import rate_limit_dependency

router = APIRouter()
logger = logging.getLogger(__name__)


class GameTokenRequest(BaseModel):
    game_id: str


class GameTokenResponse(BaseModel):
    token: str
    expires_at: str


class GuestSessionRequest(BaseModel):
    player_name: str | None = None


class GuestSessionResponse(BaseModel):
    success: bool
    session_token: str
    game_id: str | None = None
    player_id: str
    expires_at: str


@router.post(
    "/auth/game_token",
    response_model=GameTokenResponse,
    dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))],
)
def issue_game_token(req: GameTokenRequest, payload: dict = Depends(require_any_token)):
    """Issue a short-lived JWT for a given game_id to an authenticated player session."""
    if payload.get("game_id") and payload.get("game_id") != req.game_id:
        raise HTTPException(status_code=403, detail="forbidden")
    secret = os.getenv("SUECA_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="server misconfigured")
    ttl = int(os.getenv("SUECA_GAME_TOKEN_TTL", "300"))  # seconds
    now = datetime.utcnow()
    exp = now + timedelta(seconds=ttl)
    payload = {"game_id": req.game_id, "exp": int(exp.timestamp())}
    token = jwt.encode(payload, secret, algorithm="HS256")
    logger.info("Issued game token for game_id=%s by session_jti=%s", req.game_id, payload.get('jti'))
    return GameTokenResponse(token=token, expires_at=exp.isoformat() + "Z")


@router.post(
    "/auth/guest_session",
    response_model=GuestSessionResponse,
    dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))],
)
def create_guest_session(req: GuestSessionRequest):
    """
    Create a guest session token for temporary gameplay without authentication.
    
    Guest users can:
    - Create and join game rooms
    - Play games with other guests
    - Use WebSocket camera streaming
    
    Session tokens are short-lived (30 minutes) and tied to a specific player ID.
    """
    try:
        # Generate guest player ID and name
        player_id = f"guest_{uuid.uuid4().hex[:8]}"
        player_name = req.player_name or f"Guest{uuid.uuid4().hex[:4].upper()}"
        
        # Create a temporary game session (no game_id yet, will be set on room creation)
        # For now, use a placeholder that will be updated when guest joins a room
        session = session_manager.create_session(
            game_id="guest_session",  # Placeholder - will update on join
            player_id=player_id,
            player_name=player_name
        )
        
        # Get session token and expiry
        session_token = session
        session_payload = session_manager.validate_token(session_token)
        if not session_payload:
            raise HTTPException(status_code=500, detail="failed to create session")
        
        exp_time = datetime.utcfromtimestamp(session_payload.get("exp", 0))
        
        logger.info("Created guest session: player_id=%s, player_name=%s", player_id, player_name)
        
        return GuestSessionResponse(
            success=True,
            session_token=session_token,
            player_id=player_id,
            expires_at=exp_time.isoformat() + "Z"
        )
    except Exception as e:
        logger.error("Failed to create guest session: %s", e)
        raise HTTPException(status_code=500, detail="failed to create session")
