from fastapi import HTTPException
from .session import session_manager
from .core import manager


def authorize_request(token: str, game_id: str) -> dict:
    """
    Validate JWT token and ensure player is in the correct game.
    Raises HTTPException if unauthorized.
    Returns session data dict.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    session_data = session_manager.validate_token(token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if session_data["game_id"] != game_id:
        raise HTTPException(status_code=403, detail="Player not in this game")
    
    return session_data


def check_player_turn(game_id: str, player_id: str) -> bool:
    """
    Check if it's the specified player's turn.
    Returns True if it's their turn, False otherwise.
    """
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    return game.current_player and game.current_player.player_id == player_id


def check_host(game_id: str, player_id: str) -> bool:
    """
    Check if the player is the room host (creator).
    Returns True if they are, False otherwise.
    """
    game = manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    return game.creator_id == player_id
