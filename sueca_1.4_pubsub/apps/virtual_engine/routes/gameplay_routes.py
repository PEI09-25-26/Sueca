from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, conint, constr
from enum import Enum
from shared.ratelimit import rate_limit_dependency

from .common import error, get_game_from_request
from fastapi import Header
from ..auth import authorize_header, check_host, check_player_turn


router = APIRouter()


class GameRequest(BaseModel):
    game_id: str | None = None
    roomId: str | None = None


class CutDeckRequest(GameRequest):
    index: int | None = None


class SelectTrumpRequest(GameRequest):
    choice: str | None = None


class ChoiceEnum(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"


class PlayRequest(GameRequest):
    card: str | None = None


class StartRequest(GameRequest):
    pass


class ResetRequest(GameRequest):
    pass

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


@router.post("/api/start", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def start_game_endpoint(
    data: StartRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)
    session_data = authorize_header(authorization, game_id)
    check_host(game_id, session_data["player_id"])
    success, message = game.start_game()
    return {"success": success, "message": message}


@router.post("/api/cut_deck", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def cut_deck(
    data: CutDeckRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data = authorize_header(authorization, game_id)
    player_id = session_data["player_id"]
    cut_index = data.index
    if not player_id or cut_index is None:
        return error("Player and index required", 400)

    success, message = game.cut_deck(player_id, cut_index)
    if success:
        cutter = game.get_player(player_id)
        publish_deck_cut(game_id, cutter.player_name, cut_index, str(game.trump_card))
    return {"success": success, "message": message}


@router.post("/api/select_trump", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def select_trump(
    data: SelectTrumpRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data = authorize_header(authorization, game_id)
    player_id = session_data["player_id"]
    choice = data.choice
    if not player_id or not choice:
        return error("Player and choice required", 400)

    success, message = game.select_trump(player_id, choice)
    if success:
        selector = game.get_player(player_id)
        publish_trump_selected(game_id, selector.player_name, choice, str(game.trump_card))
    return {"success": success, "message": message}



@router.post("/api/play", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def play_card(
    data: PlayRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)

    card = data.card
    if not card:
        return error("Card required", 400)

    session_data = authorize_header(authorization, game_id)
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


@router.post("/api/reset", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def reset_game(
    data: ResetRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)
    session_data = authorize_header(authorization, game_id)
    check_host(game_id, session_data["player_id"])
    game.reset()
    return {"success": True, "message": "Game reset"}
