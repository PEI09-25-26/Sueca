import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query
from pydantic import BaseModel

from ..core import manager
from ..session import session_manager
from .common import error, get_game_from_request
from shared.auth import decode_access_token, extract_bearer_token
from shared.firebase_client import get_user
from shared.redis_client import get_redis



router = APIRouter()
logger = logging.getLogger(__name__)


class InviteRequest(BaseModel):
    friend_uid: str
    position: str


class DeclineInviteRequest(BaseModel):
    position: str


class RoomVisibilityRequest(BaseModel):
    game_id: Optional[str] = None
    is_public: Optional[bool] = None


class LeaveRequest(BaseModel):
    player_id: Optional[str] = None
    game_id: Optional[str] = None


def _build_requester_context(authorization: str | None) -> dict | None:
    if not authorization:
        return None

    try:
        token = extract_bearer_token(authorization)
    except HTTPException:
        return None

    session_payload = session_manager.validate_token(token) or {}

    account_payload = {}
    try:
        account_payload = decode_access_token(token)
    except HTTPException:
        account_payload = {}

    if not session_payload and not account_payload:
        return None

    uid = account_payload.get("uid") or account_payload.get("sub")
    user_data = {}
    if uid:
        try:
            user_data = get_user(str(uid)) or {}
        except Exception:
            logger.exception("Failed to load user profile for uid=%s", uid)

    username = (user_data.get("username") or user_data.get("name") or "").strip()
    return {
        "uid": str(uid) if uid else None,
        "friend_code": str(user_data.get("friendCode")) if user_data.get("friendCode") else None,
        "username": username,
        "session_game_id": session_payload.get("game_id"),
        "session_player_id": session_payload.get("player_id"),
        "session_player_name": (session_payload.get("player_name") or "").strip(),
    }


def _is_host(game, requester: dict) -> bool:
    creator_id = str(game.creator_id) if game.creator_id is not None else None
    if creator_id is None:
        return False

    candidate_ids = {
        str(v)
        for v in [
            requester.get("session_player_id"),
            requester.get("uid"),
            requester.get("friend_code"),
        ]
        if v
    }
    if creator_id in candidate_ids:
        return True

    creator_player = game.get_player(game.creator_id) if game.creator_id else None
    creator_name = (getattr(creator_player, "player_name", None) or "").strip()
    if creator_name and creator_name in {
        requester.get("session_player_name", ""),
        requester.get("username", ""),
    }:
        return True

    return False


@router.get("/api/rooms")
def list_rooms():
    rooms_payload = []

    for game_id, game in manager.games.items():
        # Hide the legacy default singleton room from public listing.
        if game_id == manager.default_game_id:
            continue

        state = game.get_state()
        players = state.get("players", [])
        rooms_payload.append(
            {
                "game_id": game_id,
                "player_count": int(state.get("player_count", len(players)) or 0),
                "max_players": int(getattr(game, "max_players", 4) or 4),
                "players": [str(p.get("name", "")) for p in players if p.get("name")],
                "phase": state.get("phase"),
                "is_public": True,
                "game_started": bool(state.get("game_started", False)),
            }
        )

    rooms_payload.sort(key=lambda room: room.get("game_id", ""))
    return {"success": True, "rooms": rooms_payload, "total_rooms": len(rooms_payload)}


@router.get("/api/invites")
def list_invites(authorization: Annotated[str | None, Header()] = None):
    requester = _build_requester_context(authorization)
    if not requester or not requester.get("uid"):
        return error("Unauthorized", 401)

    invite_key = f"invites:{requester['uid']}"
    redis = get_redis()

    invites_raw = redis.lrange(invite_key, 0, -1)
    redis.delete(invite_key)

    invites = []
    for raw in invites_raw:
        try:
            invites.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed invite payload for key=%s", invite_key)

    return {"success": True, "invites": invites}


@router.post("/api/room/{game_id}/invite")
def invite_friend(game_id: str, data: InviteRequest, authorization: Annotated[str | None, Header()] = None):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    requester = _build_requester_context(authorization)
    if not requester:
        return error("Unauthorized", 401)

    if requester.get("session_game_id") and requester.get("session_game_id") != game_id:
        return error("Invalid room token for this game", 403)

    if not _is_host(game, requester):
        return error("Only the room host can send invites", 403)

    friend_uid = (data.friend_uid or "").strip()
    if not friend_uid:
        return error("friend_uid is required", 400)

    position = (data.position or "").strip().upper()
    if not position:
        return error("position is required", 400)

    target_user = get_user(friend_uid)
    if not target_user:
        return error(f"User {friend_uid} not found", 404)

    reserved_uid = str(target_user.get("friendCode") or friend_uid)
    success, message = game.reserve_seat(reserved_uid, position)
    if not success:
        return error(message, 400)

    inviter_name = (
        requester.get("session_player_name")
        or requester.get("username")
        or "A friend"
    )
    invite_data = {
        "game_id": game_id,
        "inviter_name": inviter_name,
        "position": position,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    redis = get_redis()
    invite_key = f"invites:{friend_uid}"
    redis.lpush(invite_key, json.dumps(invite_data))
    redis.expire(invite_key, 300)

    return {"success": True, "message": f"Invitation sent to {friend_uid}"}


@router.post("/api/room/{game_id}/invite/decline")
def decline_invite(game_id: str, data: DeclineInviteRequest, authorization: Annotated[str | None, Header()] = None):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    requester = _build_requester_context(authorization)
    if not requester:
        return error("Unauthorized", 401)

    position = (data.position or "").strip().upper()
    if not position:
        return error("position is required", 400)

    candidates = []
    for candidate in [
        requester.get("friend_code"),
        requester.get("uid"),
        requester.get("session_player_id"),
    ]:
        if candidate and str(candidate) not in candidates:
            candidates.append(str(candidate))

    if not candidates:
        return error("Unable to identify user for decline operation", 400)

    first_failure = None
    for candidate_uid in candidates:
        success, message = game.release_reserved_seat(candidate_uid, position)
        if success:
            return {"success": True, "message": f"Invitation declined for position {position}"}
        if first_failure is None:
            first_failure = message

    if first_failure == "Seat reserved by another player":
        return error(first_failure, 400)

    # If reservation already expired/missing, treat decline as idempotent.
    return {"success": True, "message": f"Invitation for position {position} is no longer active"}


@router.get("/api/status")
def get_status(game_id: Annotated[Optional[str], Query()] = None):
    game, resolved_game_id = get_game_from_request(game_id_query=game_id)
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)
    return game.get_state()


@router.post("/api/room_visibility")
def update_room_visibility(
    data: RoomVisibilityRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    game, resolved_game_id = get_game_from_request(data={"game_id": data.game_id})
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)

    requester = _build_requester_context(authorization)
    if not requester:
        return error("Unauthorized", 401)

    if requester.get("session_game_id") and requester.get("session_game_id") != resolved_game_id:
        return error("Invalid room token for this game", 403)

    if not _is_host(game, requester):
        return error("Only the room host can change room visibility", 403)

    if data.is_public is None:
        return error("is_public required", 400)

    is_public = bool(data.is_public)
    game.is_public = is_public
    game._push_state("room_visibility_changed")

    message = "Room is now public" if is_public else "Room is now private"
    return {
        "success": True,
        "message": message,
        "game_id": resolved_game_id,
        "is_public": is_public,
    }


@router.post("/api/leave")
def leave_game(
    data: LeaveRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    game, resolved_game_id = get_game_from_request(data={"game_id": data.game_id})
    if not game:
        return error(f"Game {resolved_game_id} not found", 404)

    requester = _build_requester_context(authorization)
    if not requester:
        return error("Unauthorized", 401)

    if requester.get("session_game_id") and requester.get("session_game_id") != resolved_game_id:
        return error("Invalid room token for this game", 403)

    identity_ids = {
        str(v)
        for v in [
            requester.get("session_player_id"),
            requester.get("friend_code"),
            requester.get("uid"),
        ]
        if v
    }
    requested_player_id = str(data.player_id) if data.player_id else None
    if requested_player_id and requested_player_id not in identity_ids:
        return error("Forbidden: cannot leave on behalf of another player", 403)

    candidates = []
    for candidate in [
        requested_player_id,
        requester.get("session_player_id"),
        requester.get("friend_code"),
        requester.get("uid"),
    ]:
        if candidate and str(candidate) not in candidates:
            candidates.append(str(candidate))

    if not candidates:
        return error("Unable to identify player", 400)

    success = False
    message = "Player not found"
    for candidate_player_id in candidates:
        success, message = game.leave(candidate_player_id)
        if success:
            break

    if not success:
        return {"success": False, "message": message}

    try:
        token = extract_bearer_token(authorization)
        if session_manager.validate_token(token):
            session_manager.revoke_session(token)
    except HTTPException:
        pass

    # Delete room if only bots remain (and it's not the default room)
    human_players = [p for p in game.players if not getattr(p, 'is_bot', False)]
    if len(human_players) == 0 and resolved_game_id != manager.default_game_id:
        manager.delete_room(resolved_game_id)
        return {
            "success": True,
            "message": message + ". Room had only bots and has been removed.",
        }

    if len(game.players) == 0 and resolved_game_id != manager.default_game_id:
        manager.delete_room(resolved_game_id)
        return {
            "success": True,
            "message": message + ". Room was empty and has been removed.",
        }

    return {"success": True, "message": message, "game_id": resolved_game_id, "state": game.get_state()}


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
def create_game(data: Annotated[dict | None, Body()] = None):
    data = data or {}
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
def join_game(data: Annotated[dict | None, Body()] = None):
    data = data or {}
    name = data.get("name", "").strip()
    position = data.get("position")
    game_id = data.get("game_id") or manager.default_game_id
    is_bot = data.get("is_bot", False)
    if not name:
        return error("Name required", 400)

    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    success, message, player_id = game.add_player(name, position, is_bot=is_bot)
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