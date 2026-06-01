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