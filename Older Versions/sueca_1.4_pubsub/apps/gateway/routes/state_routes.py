from fastapi import APIRouter, Depends, Header, HTTPException
from shared.ratelimit import rate_limit_dependency

from .. import state
from ..dto import RoomModeDTO
from ..helpers import ingest_event, ingest_state, normalize_mode, require_any_token


router = APIRouter()


@router.post("/game/state", dependencies=[Depends(require_any_token)])
def receive_state(payload: dict):
    canonical_state = ingest_state(payload, source="virtual_engine", default_mode="virtual")
    return {
        "ok": True,
        "contract": "sueca.room_state.v1",
        "canonical": canonical_state,
    }


@router.post("/game/physical/state", dependencies=[Depends(require_any_token)])
def receive_physical_state(payload: dict):
    canonical_state = ingest_state(payload, source="physical_engine", default_mode="physical")
    return {
        "ok": True,
        "contract": "sueca.room_state.v1",
        "canonical": canonical_state,
    }


@router.post("/game/event", dependencies=[Depends(require_any_token)])
def receive_event(payload: dict):
    envelope, _ = ingest_event(payload, source="virtual_engine", default_mode="virtual")
    return {
        "ok": True,
        "contract": "sueca.event.v1",
        "event_type": envelope.event_type,
    }


@router.post("/game/physical/event", dependencies=[Depends(require_any_token)])
def receive_physical_event(payload: dict):
    envelope, _ = ingest_event(payload, source="physical_engine", default_mode="physical")
    return {
        "ok": True,
        "contract": "sueca.event.v1",
        "event_type": envelope.event_type,
    }


@router.get("/game/state", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_state(authorization: str | None = Header(default=None)):
    # Require a valid player session token (allows guest session tokens)
    from ..helpers import require_session_token
    require_session_token(authorization)
    return state.latest_state_raw


@router.get("/game/state/canonical", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_canonical_state(authorization: str | None = Header(default=None)):
    # Require a valid player session token (allows guest session tokens)
    from ..helpers import require_session_token
    require_session_token(authorization)
    return state.latest_room_state


@router.get("/game/state/canonical/{game_id}", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_canonical_state_by_game(game_id: str, authorization: str | None = Header(default=None)):
    # Require session and verify the token is for the requested game
    from ..helpers import require_session_token
    payload = require_session_token(authorization)

    # Enforce that session belongs to the requested game
    if payload.get("game_id") != game_id:
        raise HTTPException(status_code=403, detail="insufficient access to requested game state")

    return state.latest_room_state_by_game.get(game_id, {})


@router.post("/game/room_mode/{game_id}", dependencies=[Depends(require_any_token)])
def set_room_mode(game_id: str, data: RoomModeDTO):
    mode = normalize_mode(data.mode)
    state.room_modes[game_id] = mode
    return {"success": True, "game_id": game_id, "mode": mode}


@router.get("/game/room_mode/{game_id}", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_room_mode(game_id: str, authorization: str | None = Header(default=None)):
    from ..helpers import require_session_token
    payload = require_session_token(authorization)
    # allow only players of the game to query mode
    if payload.get("game_id") != game_id:
        raise HTTPException(status_code=403, detail="insufficient access to requested game mode")

    mode = state.room_modes.get(game_id, "virtual")
    return {"success": True, "game_id": game_id, "mode": mode}
