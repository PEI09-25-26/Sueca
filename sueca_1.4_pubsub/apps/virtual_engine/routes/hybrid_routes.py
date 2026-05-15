from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse
from .common import error, get_game_from_request
from ..core import manager
from ..core.hybrid_game_coordinator import HybridGameCoordinator
from ..core.hybrid_vision_service import HybridVisionService
from apps.emqx import mqtt_client


router = APIRouter()

hybrid_coordinator = HybridGameCoordinator()
hybrid_vision = HybridVisionService()


def _players_meta(game):
    return {
        p.player_id: {
            "name": p.player_name,
            "position": str(p.position),
        }
        for p in game.players
    }


def _push_hybrid_state(game, room):
    if not game or not room:
        return
    payload = {
        "event_type": "hybrid_state_update",
        "game_id": game.game_id,
        "hybrid_state": hybrid_coordinator.to_payload(room, _players_meta(game))
    }
    mqtt_client.publish_json(f"sueca/games/{game.game_id}/hybrid", payload, retain=True)


def _maybe_skip_hybrid_cut(game, room):
    if not game or not room:
        return
    if game.phase != "deck_cutting":
        return
    if not room.host_player_id and not room.player_roles:
        return

    game.phase = "trump_selection"
    game._push_state("hybrid_cut_skipped")


def _autofill_missing_real_players_for_hybrid(game):
    if not game:
        return
    if len(game.players) >= game.max_players:
        return
    if game.phase == "finished":
        return

    for position in game.positions:
        if len(game.players) >= game.max_players:
            break
        if game._get_player_by_position(position):
            continue

        base_name = f"Real_{position.name}"
        candidate = base_name
        idx = 2
        existing_names = {p.player_name for p in game.players}
        while candidate in existing_names:
            candidate = f"{base_name}_{idx}"
            idx += 1

        success, _, _ = game.add_player(candidate, position.name)
        if success:
            continue

    if len(game.players) == game.max_players:
        game._push_state("hybrid_real_players_autofilled")


@router.post("/api/hybrid/register_player")
async def hybrid_register_player(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id")
    role = data.get("role", "real")
    is_host = bool(data.get("is_host", False))

    if not player_id:
        return error("player_id is required", 400)

    if not game.get_player(player_id):
        return error("Player not found in this game", 404)

    room = hybrid_coordinator.register_player(game_id, player_id, role, is_host)
    _autofill_missing_real_players_for_hybrid(game)
    _maybe_skip_hybrid_cut(game, room)
    _push_hybrid_state(game, room)
    return {"success": True, "state": hybrid_coordinator.to_payload(room, _players_meta(game))}


@router.get("/api/hybrid/state")
async def hybrid_state(game_id: str = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)

    room = hybrid_coordinator.get_room_state(resolved_game_id)
    _autofill_missing_real_players_for_hybrid(game)
    _maybe_skip_hybrid_cut(game, room)
    return {"success": True, "state": hybrid_coordinator.to_payload(room, _players_meta(game))}


@router.post("/api/hybrid/deal/reset")
async def hybrid_deal_reset(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    host_player_id = data.get("player_id")
    cards_per_virtual = data.get("cards_per_virtual", 10)

    if not host_player_id:
        return error("player_id is required", 400)

    if game.phase != "playing":
        return {
            "success": False,
            "message": "Hybrid card assignment is only available after trump selection (playing phase)",
            "phase": game.phase,
        }

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id and room.host_player_id != host_player_id:
        return error("Only host can reset deal", 403)

    registered_virtual_ids = [
        pid for pid, role in room.player_roles.items()
        if role == "virtual" and game.get_player(pid) is not None and pid != host_player_id
    ]

    if not (0 <= len(registered_virtual_ids) <= 3):
        return error("Hybrid mode supports up to 3 virtual players", 400)

    room = hybrid_coordinator.reset_deal(
        game_id=game_id,
        host_player_id=host_player_id,
        virtual_player_ids=registered_virtual_ids,
        cards_per_virtual=cards_per_virtual,
    )
    _push_hybrid_state(game, room)
    return {"success": True, "state": hybrid_coordinator.to_payload(room, _players_meta(game))}


@router.post("/api/hybrid/trump/confirm_capture")
async def hybrid_confirm_trump_capture(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    host_player_id = data.get("host_player_id")
    frame_base64 = data.get("frame_base64")

    if not host_player_id or not frame_base64:
        return error("host_player_id and frame_base64 are required", 400)

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)

    if game.phase != "trump_selection":
        return error("Not in trump selection phase", 409)

    if room.host_player_id and host_player_id != room.host_player_id:
        return error("Only host can submit trump frame", 403)

    selector = game._get_player_by_position(game._current_dealer_position())
    if selector is None:
        return error("Trump selector player not found", 400)

    recognized = await hybrid_vision.recognize_once(game_id, frame_base64)
    if recognized is None:
        return error("No valid card detected", 400)

    success, message = game.select_trump_by_card(selector.player_id, recognized.card_id)
    if not success:
        return error(message, 400)

    response_payload = {
        "success": True,
        "message": message,
        "captured_card_id": recognized.card_id,
        "captured_display": recognized.display,
        "game_state": game.get_state(),
        "state": hybrid_coordinator.to_payload(room, _players_meta(game)),
    }
    _push_hybrid_state(game, room)
    return response_payload


@router.post("/api/hybrid/deal/recognize")
async def hybrid_deal_recognize(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    host_player_id = data.get("player_id")
    frame_base64 = data.get("frame_base64")
    target_player_id = data.get("target_player_id")

    if not host_player_id:
        return error("player_id is required", 400)
    if not frame_base64:
        return error("frame_base64 is required", 400)

    if game.phase != "playing":
        return {
            "success": False,
            "recognized": False,
            "confirmed": False,
            "message": "Waiting for trump selection to finish before dealing virtual cards",
            "phase": game.phase,
            "state": hybrid_coordinator.to_payload(hybrid_coordinator.get_room_state(game_id), _players_meta(game)),
        }

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id and room.host_player_id != host_player_id:
        return error("Only host can process deal frames", 403)

    recognized = await hybrid_vision.recognize_once(game_id, frame_base64)
    if recognized is None:
        return {
            "success": True,
            "recognized": False,
            "confirmed": False,
            "message": "No valid card detected",
            "state": hybrid_coordinator.to_payload(room, _players_meta(game)),
        }

    target = target_player_id or hybrid_coordinator.deal_next_target(game_id)
    if not target:
        return {
            "success": True,
            "recognized": True,
            "confirmed": False,
            "message": "All virtual players already have their cards",
            "card": {"id": recognized.card_id, "display": recognized.display},
            "state": hybrid_coordinator.to_payload(room, _players_meta(game)),
        }

    ok, message, room = hybrid_coordinator.add_deal_card(game_id, target, recognized.card_id)
    response_payload = {
        "success": True,
        "recognized": True,
        "confirmed": ok,
        "message": message,
        "target_player_id": target,
        "card": {
            "id": recognized.card_id,
            "rank": recognized.rank,
            "suit": recognized.suit_name,
            "suit_symbol": recognized.suit_symbol,
            "drawable_key": recognized.drawable_key,
            "display": recognized.display,
        },
        "state": hybrid_coordinator.to_payload(room, _players_meta(game)),
    }
    _push_hybrid_state(game, room)
    return response_payload


@router.post("/api/hybrid/virtual/select_card")
async def hybrid_virtual_select_card(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id")
    card = data.get("card")

    if not player_id or card is None:
        return error("player_id and card are required", 400)

    try:
        card = int(card)
    except (TypeError, ValueError):
        return error("card must be an integer", 400)

    ok, message, room = hybrid_coordinator.select_virtual_card(game_id, player_id, card)
    status = 200 if ok else 400
    payload = {"success": ok, "message": message, "state": hybrid_coordinator.to_payload(room, _players_meta(game))}
    if ok:
        _push_hybrid_state(game, room)
    return payload if status == 200 else error(payload["message"], status)


@router.get("/api/hybrid/pending_play")
async def hybrid_pending_play(game_id: str = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)

    room = hybrid_coordinator.get_room_state(resolved_game_id)
    payload = hybrid_coordinator.to_payload(room, _players_meta(game))
    return {"success": True, "pending": payload.get("pending_virtual_play"), "state": payload}


@router.post("/api/hybrid/play/confirm_capture")
async def hybrid_confirm_capture(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id")
    host_player_id = data.get("host_player_id")
    frame_base64 = data.get("frame_base64")

    if not player_id or not frame_base64:
        return error("player_id and frame_base64 are required", 400)

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id:
        if not host_player_id:
            return error("host_player_id is required for capture confirmation", 400)
        if host_player_id != room.host_player_id:
            return error("Only host can submit capture frames", 403)

    recognized = await hybrid_vision.recognize_once(game_id, frame_base64)
    if recognized is None:
        return error("No valid card detected", 400)

    recognized_card = str(recognized.card_id)
    room = hybrid_coordinator.get_room_state(game_id)
    pending = room.pending_virtual_play

    if pending and pending.player_id == player_id:
        if int(recognized.card_id) != int(pending.card_id):
            return error("Captured card does not match selected virtual card", 400)

    success, message = game.play_card_hybrid_capture(player_id, recognized_card)
    if not success:
        return error(message, 400)

    room = hybrid_coordinator.confirm_play_success(game_id, player_id, recognized.card_id)
    response_payload = {
        "success": True,
        "message": message,
        "captured_card_id": recognized.card_id,
        "captured_display": recognized.display,
        "state": hybrid_coordinator.to_payload(room, _players_meta(game)),
        "game_state": game.get_state(),
    }
    _push_hybrid_state(game, room)
    return response_payload
