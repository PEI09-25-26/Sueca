from typing import Optional
import uuid

from fastapi import APIRouter, Body, Header, Query, Depends
from shared.ratelimit import rate_limit_dependency
from pydantic import BaseModel, constr

from ..auth import authorize_header, check_host
from ..core import manager
from ..session import session_manager
from .common import error, get_game_from_request


router = APIRouter()


class CreateRoomRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=64)] = None
    position: Optional[str] = None


class CreateGameRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=64)
    position: Optional[str] = None


class JoinRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=64)
    position: Optional[str] = None
    game_id: Optional[str] = None


class RoomVisibilityRequest(BaseModel):
    game_id: Optional[str] = None
    is_public: Optional[bool] = None


class LeaveRequest(BaseModel):
    player_id: Optional[str] = None
    game_id: Optional[str] = None


@router.get("/api/status", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_status(game_id: Optional[str] = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)
    return game.get_state()


@router.get("/api/rooms", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def list_rooms(
    include_default: bool = Query(default=False),
    include_empty: bool = Query(default=True),
    include_full: bool = Query(default=True),
    include_private: bool = Query(default=False),
):
    rooms = []

    for game_id, game in manager.games.items():
        if not include_default and game_id == manager.default_game_id:
            continue

        game_state = game.get_state()
        is_public = bool(game_state.get("is_public", getattr(game, "is_public", True)))
        if not include_private and not is_public:
            continue

        player_count = int(game_state.get("player_count", 0))
        max_players = int(getattr(game, "max_players", 4))
        if not include_empty and player_count == 0:
            continue
        if not include_full and player_count >= max_players:
            continue

        rooms.append(
            {
                "game_id": game_id,
                "player_count": player_count,
                "max_players": max_players,
                "players": [p.get("name", "") for p in game_state.get("players", [])],
                "phase": game_state.get("phase"),
                "is_public": is_public,
                "game_started": bool(game_state.get("game_started", False)),
            }
        )

    return {
        "success": True,
        "rooms": rooms,
        "total_rooms": len(rooms),
    }


@router.get("/api/room/{game_id}/lobby", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_room_lobby(game_id: str, authorization: str | None = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)
    # Require authentication to view lobby details
    session_data = authorize_header(authorization, game_id)

    state = game.get_state()
    return {
        "success": True,
        "game_id": game_id,
        "phase": state.get("phase"),
        "player_count": state.get("player_count", 0),
        "max_players": game.max_players,
        "available_slots": state.get("available_slots", []),
        "teams": {
            "team1": state.get("teams", {}).get("team1", []),
            "team2": state.get("teams", {}).get("team2", []),
        },
    }


@router.get("/api/room/{game_id}/history", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_room_history(game_id: str, authorization: str | None = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)
    # Require authentication to access match history
    session_data = authorize_header(authorization, game_id)

    return {
        "success": True,
        "game_id": game_id,
        "matches_played": len(game.match_history),
        "history": game.match_history,
    }


@router.get("/api/room/{game_id}/match_points", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_room_match_points(game_id: str, authorization: str | None = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)
    # Require authentication to view match points
    session_data = authorize_header(authorization, game_id)

    return {
        "success": True,
        "game_id": game_id,
        "points": {
            "team1": game.match_points["team1"],
            "team2": game.match_points["team2"],
        },
        "teams": {
            "team1": [player.player_name for player in game.teams[0]],
            "team2": [player.player_name for player in game.teams[1]],
        },
        "matches_played": len(game.match_history),
    }


@router.post("/api/room/{game_id}/rematch", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def start_room_rematch(game_id: str, authorization: str = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)
    session_data = authorize_header(authorization, game_id)
    check_host(game_id, session_data["player_id"])

    success, message = game.rematch()
    if not success:
        return error(message, 400)
    return {"success": True, "message": message, "state": game.get_state()}


@router.post("/api/create_room", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def create_room_endpoint(data: CreateRoomRequest = Body(default_factory=dict)):
    name = data.name.strip() if data.name else ""
    position = data.position
    if name:
        success, message, game_id, player_id = manager.create_room_with_host(name, position)
        if not success:
            return error(message, 400)

        token = session_manager.create_session(game_id, player_id, name)
        return {
            "success": True,
            "message": message,
            "game_id": game_id,
            "player_id": player_id,
            "token": token,
        }

    game_id = manager.create_room()
    return {"success": True, "game_id": game_id}


@router.post("/api/create_game", dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))])
def create_game(data: CreateGameRequest = Body(...)):
    name = data.name.strip()
    position = data.position

    success, message, game_id, player_id = manager.create_game(name, position)
    return {
        "success": success,
        "message": message,
        "game_id": game_id,
        "player_id": player_id,
    }


@router.post("/api/join", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def join_game(data: JoinRequest = Body(...), authorization: str | None = Header(default=None)):
    name = data.name.strip()
    position = data.position
    game_id = data.game_id or manager.default_game_id

    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id_override = None
    if authorization:
        try:
            session_data = authorize_header(authorization, game_id)
            if session_data.get("player_id") == game.creator_id:
                player_id_override = session_data.get("player_id")
        except Exception:
            player_id_override = None

    success, message, player_id = game.add_player(name, position, player_id=player_id_override)
    if success:
        # Rooms created with create_room start empty; first joiner becomes host.
        if game.creator_id is None:
            game.creator_id = player_id
        # Issue token
        token = session_manager.create_session(game_id, player_id, name)
        return {
            "success": True,
            "message": message,
            "game_id": game_id,
            "player_id": player_id,
            "token": token
        }
    
    return {"success": False, "message": message}

@router.post("/api/room_visibility", dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))])
def update_room_visibility(
    data: RoomVisibilityRequest = Body(...),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request({"game_id": data.game_id})
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data = authorize_header(authorization, game_id)
    actor_id = session_data["player_id"]
    check_host(game_id, actor_id)

    if data.is_public is None:
        return error("is_public required", 400)

    is_public = bool(data.is_public)

    game.is_public = is_public
    game._push_state("room_visibility_changed")

    message = "Room is now public" if is_public else "Room is now private"
    return {"success": True, "message": message, "game_id": game_id, "is_public": is_public}

@router.post("/api/leave", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def leave_game(
    data: LeaveRequest = Body(default_factory=dict),
    authorization: str = Header(default=None),
):
    game, game_id = get_game_from_request(data.dict())
    if not game:
        return error(f"Game {game_id} not found", 404)

    session_data = authorize_header(authorization, game_id)
    player_id = session_data["player_id"]

    # Voluntary leave: allow leaving if game not started, or if finished (e.g. before rematch)
    success, message = game.leave(player_id)
    if not success:
        return {"success": False, "message": message}

    # Clean up sessions for this player
    session_manager.delete_sessions_for_player(player_id)

    # If room is empty after leaving, delete the room
    if len(game.players) == 0:
        manager.delete_room(game_id)
        return {"success": True, "message": message + ". Room was empty and has been removed."}

    # If the creator was reassigned, inform clients via returned state
    return {"success": True, "message": message, "game_id": game_id, "state": game.get_state()}
