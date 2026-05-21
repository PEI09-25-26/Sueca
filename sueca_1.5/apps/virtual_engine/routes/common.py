from typing import Optional

from fastapi.responses import JSONResponse

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
