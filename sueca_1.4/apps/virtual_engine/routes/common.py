from typing import Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..auth import authorize_request
from ..core import manager


def error(message: str, status_code: int):
    return JSONResponse(status_code=status_code, content={"success": False, "message": message})


def get_game_from_request(data: Optional[dict] = None, game_id_query: Optional[str] = None):
    game_id = None
    if isinstance(data, dict):
        game_id = data.get("game_id")
    if not game_id:
        game_id = game_id_query
    if not game_id:
        game_id = manager.default_game_id

    game = manager.get_game(game_id)
    return game, game_id


def get_authenticated_player(authorization: Optional[str], game_id: str):
    if not authorization:
        return None, error("Missing authorization header", 401)

    if not authorization.startswith("Bearer "):
        return None, error("Invalid authorization header format", 401)

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None, error("Missing bearer token", 401)

    try:
        session_data = authorize_request(token, game_id)
    except HTTPException as exc:
        return None, error(str(exc.detail), exc.status_code)

    return session_data, None
