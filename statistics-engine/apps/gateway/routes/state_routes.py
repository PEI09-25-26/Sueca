from fastapi import APIRouter

from .. import state
from ..dto import RoomModeDTO
from ..helpers import ingest_event, ingest_state, normalize_mode


router = APIRouter()


@router.post("/game/state")
def receive_state(payload: dict):
    canonical_state = ingest_state(payload, source="virtual_engine", default_mode="virtual")
    return {
        "ok": True,
        "contract": "sueca.room_state.v1",
        "canonical": canonical_state,
    }


@router.post("/game/physical/state")
def receive_physical_state(payload: dict):
    canonical_state = ingest_state(payload, source="physical_engine", default_mode="physical")
    return {
        "ok": True,
        "contract": "sueca.room_state.v1",
        "canonical": canonical_state,
    }


@router.post("/game/event")
def receive_event(payload: dict):
    envelope, _ = ingest_event(payload, source="virtual_engine", default_mode="virtual")
    return {
        "ok": True,
        "contract": "sueca.event.v1",
        "event_type": envelope.event_type,
    }


@router.post("/game/physical/event")
def receive_physical_event(payload: dict):
    envelope, _ = ingest_event(payload, source="physical_engine", default_mode="physical")
    return {
        "ok": True,
        "contract": "sueca.event.v1",
        "event_type": envelope.event_type,
    }


@router.get("/game/state")
def get_state():
    return state.latest_state_raw


@router.get("/game/state/canonical")
def get_canonical_state():
    return state.latest_room_state


@router.get("/game/state/canonical/{game_id}")
def get_canonical_state_by_game(game_id: str):
    return state.latest_room_state_by_game.get(game_id, {})


@router.post("/game/room_mode/{game_id}")
def set_room_mode(game_id: str, data: RoomModeDTO):
    mode = normalize_mode(data.mode)
    state.room_modes[game_id] = mode
    return {"success": True, "game_id": game_id, "mode": mode}


@router.get("/game/room_mode/{game_id}")
def get_room_mode(game_id: str):
    mode = state.room_modes.get(game_id, "virtual")
    return {"success": True, "game_id": game_id, "mode": mode}
