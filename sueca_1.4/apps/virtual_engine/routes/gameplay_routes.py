from fastapi import APIRouter, Body, Header

from ..auth import check_host, check_player_turn
from .common import error, get_authenticated_player, get_game_from_request


router = APIRouter()

try:
    from ..event_publisher import (
        publish_game_started,
        publish_deck_cut,
        publish_trump_selected,
        publish_card_played,
    )
except ImportError:
    def publish_game_started(*args, **kwargs):
        return None

    def publish_deck_cut(*args, **kwargs):
        return None

    def publish_trump_selected(*args, **kwargs):
        return None

    def publish_card_played(*args, **kwargs):
        return None


@router.post("/api/start")
def start_game_endpoint(
    data: dict = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data, auth_error = get_authenticated_player(authorization, game_id)
    if auth_error:
        return auth_error

    if not check_host(game_id, session_data["player_id"]):
        return error("Only room creator can start the game", 403)

    success, message = game.start_game()
    if success:
        publish_game_started(game_id)
    return {"success": success, "message": message}


@router.post("/api/cut_deck")
def cut_deck(
    data: dict = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data, auth_error = get_authenticated_player(authorization, game_id)
    if auth_error:
        return auth_error

    player_id = session_data["player_id"]
    cut_index = data.get("index")
    if cut_index is None:
        return error("Index required", 400)

    success, message = game.cut_deck(player_id, cut_index)
    if success:
        cutter = game.get_player(player_id)
        if cutter:
            publish_deck_cut(game_id, cutter.player_name, cut_index, str(game.trump_card))
    return {"success": success, "message": message}


@router.post("/api/select_trump")
def select_trump(
    data: dict = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data, auth_error = get_authenticated_player(authorization, game_id)
    if auth_error:
        return auth_error

    player_id = session_data["player_id"]
    choice = data.get("choice")
    if not choice:
        return error("Choice required", 400)

    success, message = game.select_trump(player_id, choice)
    if success:
        selector = game.get_player(player_id)
        if selector:
            publish_trump_selected(game_id, selector.player_name, choice, str(game.trump_card))
    return {"success": success, "message": message}


@router.post("/api/play")
def play_card(
    data: dict = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data, auth_error = get_authenticated_player(authorization, game_id)
    if auth_error:
        return auth_error

    player_id = session_data["player_id"]
    card = data.get("card")
    if card is None:
        return error("Card required", 400)

    if not check_player_turn(game_id, player_id):
        return error("Not your turn", 403)

    success, message = game.play_card(player_id, str(card))
    if success:
        player = game.get_player(player_id)
        if player:
            publish_card_played(game_id, player.player_id, player.player_name, str(card), game.current_round)
    return {"success": success, "message": message}


@router.post("/api/reset")
def reset_game(
    data: dict = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data, auth_error = get_authenticated_player(authorization, game_id)
    if auth_error:
        return auth_error

    if not check_host(game_id, session_data["player_id"]):
        return error("Only room creator can reset the game", 403)

    game.reset()
    return {"success": True, "message": "Game reset"}
