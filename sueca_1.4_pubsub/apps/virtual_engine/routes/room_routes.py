from typing import Optional

from fastapi import APIRouter, Body, Query

from ..core import manager
from ..session import session_manager
from .common import error, get_game_from_request



router = APIRouter()


@router.get("/api/status")
def get_status(game_id: Optional[str] = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)
    return game.get_state()


@router.get("/api/rooms")
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


@router.get("/api/room/{game_id}/lobby")
def get_room_lobby(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

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


@router.get("/api/room/{game_id}/history")
def get_room_history(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    return {
        "success": True,
        "game_id": game_id,
        "matches_played": len(game.match_history),
        "history": game.match_history,
    }


@router.get("/api/room/{game_id}/match_points")
def get_room_match_points(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

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


@router.post("/api/room/{game_id}/rematch")
def start_room_rematch(game_id: str):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    success, message = game.rematch()
    if not success:
        return error(message, 400)
    return {"success": True, "message": message, "state": game.get_state()}


@router.post("/api/create_room")
def create_room_endpoint():
    game_id = manager.create_room()
    return {"success": True, "game_id": game_id}


@router.post("/api/create_game")
def create_game(data: dict = Body(default_factory=dict)):
    name = data.get("name", "").strip()
    position = data.get("position")
    if not name:
        return error("Name required", 400)

    success, message, game_id, player_id = manager.create_game(name, position)
    return {
        "success": success,
        "message": message,
        "game_id": game_id,
        "player_id": player_id,
    }


@router.post("/api/join")
def join_game(data: dict = Body(default_factory=dict)):
    name = data.get("name", "").strip()
    position = data.get("position")
    game_id = data.get("game_id") or manager.default_game_id
    if not name:
        return error("Name required", 400)

    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    success, message, player_id = game.add_player(name, position)
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

@router.post("/api/room_visibility")
def update_room_visibility(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    actor_id = data.get("player_id") or data.get("actor_id")
    if not actor_id:
        return error("player_id required", 400)
    if not game.creator_id or game.creator_id != actor_id:
        return error("Only room creator can change room visibility", 403)

    if "is_public" not in data:
        return error("is_public required", 400)

    raw_visibility = data.get("is_public")
    if isinstance(raw_visibility, bool):
        is_public = raw_visibility
    else:
        visibility_value = str(raw_visibility).strip().lower()
        if visibility_value in {"1", "true", "yes", "public"}:
            is_public = True
        elif visibility_value in {"0", "false", "no", "private"}:
            is_public = False
        else:
            return error("Invalid is_public value", 400)

    game.is_public = is_public
    game._push_state("room_visibility_changed")

    message = "Room is now public" if is_public else "Room is now private"
    return {"success": True, "message": message, "game_id": game_id, "is_public": is_public}