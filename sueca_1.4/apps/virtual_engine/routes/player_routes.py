from fastapi import APIRouter, Body, Query

from ..core import BotFactory
from .common import error, get_game_from_request


router = APIRouter()


@router.post("/api/change_position")
def change_position(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    player_id = data.get("player_id") or data.get("player")
    new_position = data.get("position")
    if not player_id or not new_position:
        return error("Player and new position required", 400)

    player = game.get_player(player_id)
    if not player:
        return error("Player not found", 404)
    if game.game_started:
        return error("Cannot change position after game has started", 400)

    normalized_new_position = game._normalize_position(new_position)
    if not normalized_new_position:
        return error("Invalid position. Choose NORTH, SOUTH, EAST, or WEST", 400)
    if player.position == normalized_new_position:
        return {"success": True, "message": "Position unchanged", "state": game.get_state()}

    for other_player in game.players:
        if getattr(other_player, "player_id", None) != player_id and other_player.position == normalized_new_position:
            return error(f"Position {new_position} is already taken by {other_player.player_name}", 400)

    old_position = player.position
    old_team_key = "team1" if old_position in game._TEAM1_POSITIONS else "team2"
    new_team_key = "team1" if normalized_new_position in game._TEAM1_POSITIONS else "team2"

    if old_position not in game.available_team_positions[old_team_key]:
        game.available_team_positions[old_team_key].append(old_position)
    if normalized_new_position not in game.available_team_positions[new_team_key]:
        return error(f"Position {new_position} is not available", 400)
    game.available_team_positions[new_team_key].remove(normalized_new_position)

    game.teams[0] = [member for member in game.teams[0] if getattr(member, "player_id", None) != player_id]
    game.teams[1] = [member for member in game.teams[1] if getattr(member, "player_id", None) != player_id]
    player.position = normalized_new_position
    if new_team_key == "team1":
        game.teams[0].append(player)
    else:
        game.teams[1].append(player)

    game._push_state("position_changed")
    return {"success": True, "message": f"Position changed to {player.position.name}", "state": game.get_state()}


@router.post("/api/add_bot")
def add_bot(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    requester_id = data.get("player_id")
    if not requester_id:
        return error("player_id required", 400)
    if game.creator_id != requester_id:
        return error("Only room creator can add bots", 403)

    position = data.get("position")
    if not position:
        return error("Position required", 400)
    if game.game_started:
        return error("Cannot add bots after game has started", 400)

    bot_name = data.get("name", f"Bot_{position}")
    difficulty = data.get("difficulty", "random")
    agent = BotFactory.create_bot(bot_name, position, game_id, difficulty)
    if not agent:
        available = ", ".join(BotFactory.get_available_bots())
        return error(f"Unknown bot type. Available: {available}", 400)

    import time

    time.sleep(0.5)
    bot_player = next((player for player in game.players if player.player_name == bot_name), None)
    if bot_player:
        return {
            "success": True,
            "message": f"Bot {bot_name} added at position {position}",
            "game_id": game_id,
            "player_id": bot_player.player_id,
        }

    return {
        "success": True,
        "message": f"Bot {bot_name} is joining...",
        "game_id": game_id,
        "player_id": None,
    }


@router.get("/api/hand/{player_id}")
def get_hand(player_id: str, game_id: str | None = Query(default=None)):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)

    player = game.get_player(player_id)
    if not player:
        return error("Player not found", 404)
    return {"success": True, "hand": [str(card) for card in player.hand]}


@router.post("/api/remove_player")
@router.post("/api/the_council_has_decided_your_fate")
def remove_player_endpoint(data: dict = Body(default_factory=dict)):
    game, game_id = get_game_from_request(data)
    if not game:
        return error(f"Game {game_id} not found", 404)

    actor_id = data.get("actor_id")
    target_id = data.get("target_id")
    if not actor_id or not target_id:
        return error("Both actor_id and target_id are required", 400)

    success, message = game.remove_player(actor_id, target_id)
    return {"success": success, "message": message}
