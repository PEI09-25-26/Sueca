from typing import Optional

from fastapi import APIRouter, Body, Query

from ..core import manager
from ..session import session_manager
from .common import error, get_game_from_request

# Injected at startup by hybrid engine main — same singletons used by hybrid_routes.
hybrid_coordinator = None
hybrid_vision = None


router = APIRouter()


@router.get("/api/status")
def get_status(game_id: Optional[str] = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)
    return game.get_state()


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

    if hybrid_coordinator is not None:
        room = hybrid_coordinator.reset_for_rematch(game_id)

        # Skip cutting phase since hybrid games do not cut.
        from apps.hybrid_engine.routes.hybrid_routes import _maybe_skip_hybrid_cut
        _maybe_skip_hybrid_cut(game, room)

        # Push a FRESH hybrid state to MQTT so the retained message on
        # `sueca/games/{game_id}/hybrid` is overwritten with deal_done=False
        # and empty bot hands. Without this, Android would read the stale
        # retained message and think the deal is already complete.
        from apps.hybrid_engine.core.hybrid_services import _push_hybrid_state_fn
        if _push_hybrid_state_fn is not None:
            _push_hybrid_state_fn(game, room)

    # ── CV vision service ──────────────────────────────────────────────────
    # Fully clear the per-game CV state and restart in trump-detection mode.
    # `clear_game` removes all consumed/dealt card memory from the previous
    # match. `begin_trump_phase` sets the phase back to "trump" so the camera
    # correctly looks for the new trump card instead of play cards.
    if hybrid_vision is not None:
        hybrid_vision.clear_game(game_id)
        hybrid_vision.begin_trump_phase(game_id)

    return {"success": True, "message": message, "state": game.get_state()}




@router.post("/api/create_room")
def create_room_endpoint():
    game_id = manager.create_room()
    try:
        import apps.hybrid_engine.routes.hybrid_routes as hybrid_routes_module

        vision = hybrid_routes_module.hybrid_vision
        if vision is not None:
            vision.clear_game(game_id)
            vision.begin_trump_phase(game_id)
    except Exception:
        pass
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