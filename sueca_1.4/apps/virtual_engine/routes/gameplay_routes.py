from fastapi import APIRouter, Body

from .common import error, get_game_from_request


router = APIRouter()


@router.post("/api/start")
def start_game_endpoint(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)
    success, message = game.start_game()
    return {"success": success, "message": message}


@router.post("/api/cut_deck")
def cut_deck(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id") or data.get("player")
    cut_index = data.get("index")
    if not player_id or cut_index is None:
        return error("Player and index required", 400)

    success, message = game.cut_deck(player_id, cut_index)
    return {"success": success, "message": message}


@router.post("/api/select_trump")
def select_trump(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id") or data.get("player")
    choice = data.get("choice")
    if not player_id or not choice:
        return error("Player and choice required", 400)

    success, message = game.select_trump(player_id, choice)
    return {"success": success, "message": message}


@router.post("/api/play")
def play_card(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id") or data.get("player")
    card = data.get("card")
    if not player_id or card is None:
        return error("Player and card required", 400)

    success, message = game.play_card(player_id, str(card))
    return {"success": success, "message": message}


@router.post("/api/reset")
def reset_game(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)
    game.reset()
    return {"success": True, "message": "Game reset"}
