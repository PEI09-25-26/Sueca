"""Authorization and permission checks."""

from fastapi import HTTPException, status
from .session import session_manager
from .core import manager


def authorize_request(token: str, game_id: str) -> dict:
    """
    Validate token and check player is in the correct game.
    Returns session data if valid.
    """
    session_data = session_manager.validate_token(token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    if session_data['game_id'] != game_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Player not in this game"
        )
    
    return session_data


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


def authorize_header(authorization: str | None, game_id: str) -> dict:
    token = extract_bearer_token(authorization)
    return authorize_request(token, game_id)


def identify_user(authorization: str | None) -> dict:
    """Extracts user identification from either session or account token."""
    import logging
    logger = logging.getLogger("virtual_engine.auth")
    
    if not authorization or not authorization.startswith("Bearer "):
        logger.debug("identify_user: No valid authorization header")
        return {}
    token = authorization[7:].strip()

    # 1. Try session token
    from .session import session_manager
    try:
        session_data = session_manager.validate_token(token)
        if session_data:
            logger.debug(f"identify_user: Found session token for player {session_data.get('player_id')}")
            return {
                "uid": session_data.get("player_id"),
                "name": session_data.get("player_name")
            }
    except Exception as e:
        logger.debug(f"identify_user: Session token validation failed: {e}")

    # 2. Try account token
    try:
        from shared.auth import decode_access_token
        payload = decode_access_token(token)
        uid = payload.get("uid") or payload.get("sub")
        name = payload.get("username") or payload.get("name")
        logger.debug(f"identify_user: Found account token for uid {uid}")
        return {
            "uid": uid,
            "name": name
        }
    except Exception as e:
        logger.debug(f"identify_user: Account token validation failed: {e}")
        return {}


def check_player_turn(game_id: str, player_id: str):
    """Check if it's the player's turn."""
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.current_player and game.current_player.player_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not your turn. Waiting for {game.current_player.player_name}"
        )


def check_host(game_id: str, player_id: str):
    """Check if player is the room creator/host."""
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.creator_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room creator can perform this action"
        )
