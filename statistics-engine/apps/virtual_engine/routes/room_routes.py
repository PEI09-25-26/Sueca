import time
from typing import Optional

from fastapi import APIRouter, Body, Query

from ..core import BotFactory, launch_bot_thread, manager
from ..session import session_manager
from .common import error, get_game_from_request



router = APIRouter()


def _normalize_bot_specs(bots_payload):
    default_bots = [
        {"name": "Rita", "position": "NORTH", "difficulty": "random"},
        {"name": "Alyssa", "position": "EAST", "difficulty": "weak"},
        {"name": "Ava", "position": "SOUTH", "difficulty": "average"},
        {"name": "Serana", "position": "WEST", "difficulty": "random"},
    ]

    bots = bots_payload if isinstance(bots_payload, list) and bots_payload else default_bots
    if len(bots) != 4:
        raise ValueError("bots must contain exactly 4 entries")

    normalized = []
    seen_positions = set()
    seen_names = set()
    for index, bot in enumerate(bots, start=1):
        if not isinstance(bot, dict):
            raise ValueError(f"bot #{index} must be an object")

        name = str(bot.get("name") or f"Bot{index}").strip()
        position = str(bot.get("position") or "").strip().upper()
        difficulty = str(bot.get("difficulty") or "random").strip().lower()

        if not name:
            raise ValueError(f"bot #{index} has an empty name")
        if position not in {"NORTH", "EAST", "SOUTH", "WEST"}:
            raise ValueError(f"invalid position for {name}: {position}")
        if position in seen_positions:
            raise ValueError(f"duplicate position: {position}")
        if name in seen_names:
            raise ValueError(f"duplicate bot name: {name}")

        seen_positions.add(position)
        seen_names.add(name)
        normalized.append({"name": name, "position": position, "difficulty": difficulty})

    return normalized


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
    return {"success": True, "message": message, "state": game.get_state()}


@router.post("/api/create_room")
def create_room_endpoint():
    game_id = manager.create_room()
    return {"success": True, "game_id": game_id}


@router.post("/api/create_bot_match")
def create_bot_match(data: dict = Body(default_factory=dict)):
    join_timeout_sec = float(data.get("join_timeout_sec", 8.0) or 8.0)
    fast_mode = bool(data.get("fast_mode"))
    try:
        bots = _normalize_bot_specs(data.get("bots"))
    except ValueError as validation_error:
        return error(str(validation_error), 400)

    game_id = manager.create_room()
    game = manager.get_game(game_id)
    if not game:
        return error("Failed to create game room", 500)

    game.set_fast_mode(fast_mode)

    try:
        for bot in bots:
            agent = BotFactory.create_bot(bot["name"], bot["position"], game_id, bot["difficulty"])
            if not agent:
                return error(f"Unknown bot difficulty for {bot['name']}: {bot['difficulty']}", 400)

            if not launch_bot_thread(agent, game_id=game_id, bot_name=bot["name"]):
                return error(f"Bot thread already running for {bot['name']} in game {game_id}", 409)

        deadline = time.time() + max(0.0, join_timeout_sec)
        while time.time() < deadline:
            if len(game.players) == 4:
                break

        return {
            "success": True,
            "game_id": game_id,
            "players": len(game.players),
            "phase": game.phase,
            "bots": bots,
        }
    except Exception as ex:
        return error(f"Failed to create bot match: {ex}", 500)


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