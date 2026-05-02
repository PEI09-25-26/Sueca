from fastapi import APIRouter, Body

from .common import error, get_game_from_request
from fastapi import Header
from ..auth import authorize_request, check_player_turn


router = APIRouter()

try:
    from ..event_publisher import (
        publish_game_started, publish_deck_cut, publish_trump_selected, publish_card_played
    )
except ImportError:
    # Events module not available or game running without MQTT
    def publish_game_started(*args, **kwargs):
        # Intentionally no-op when MQTT event publisher is unavailable.
        return None

    def publish_deck_cut(*args, **kwargs):
        # Intentionally no-op when MQTT event publisher is unavailable.
        return None

    def publish_trump_selected(*args, **kwargs):
        # Intentionally no-op when MQTT event publisher is unavailable.
        return None

    def publish_card_played(*args, **kwargs):
        # Intentionally no-op when MQTT event publisher is unavailable.
        return None


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
    if success:
        cutter = game.get_player(player_id)
        publish_deck_cut(game_id, cutter.player_name, cut_index, str(game.trump_card))
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
    if success:
        selector = game.get_player(player_id)
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

    card = data.get("card")
    if not card:
        return error("Card required", 400)

    player_id = data.get("player_id") or data.get("player")

    # If a bearer token is provided, use it as the source of truth for player identity.
    if authorization:
        if not authorization.startswith("Bearer "):
            return error("Invalid authorization header format", 401)
        token = authorization[7:]
        session_data = authorize_request(token, game_id)
        player_id = session_data["player_id"]
        check_player_turn(game_id, player_id)

    if not player_id:
        return error("Player required", 400)

    success, message = game.play_card(player_id, card)

    if success:
        # Route-level state push acts as a safety net if deeper game-core push is bypassed.
        game._push_state("card_played")
        player = game.get_player(player_id)
        if player:
            publish_card_played(game_id, player.player_id, player.player_name, card, game.current_round)

    return {"success": success, "message": message}


@router.post("/api/reset")
def reset_game(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)
    game.reset()
    return {"success": True, "message": "Game reset"}
