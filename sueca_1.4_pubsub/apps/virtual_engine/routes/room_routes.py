from typing import Optional
import uuid
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Body, Header, Query, Depends
from shared.ratelimit import rate_limit_dependency
from pydantic import BaseModel, constr

from ..auth import authorize_header, check_host, identify_user
from ..core import manager
from ..session import session_manager
from .common import error, get_game_from_request


router = APIRouter()
logger = logging.getLogger(__name__)


class CreateRoomRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=64)] = None
    position: Optional[str] = None
    player_id: Optional[str] = None


class CreateGameRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=64)
    position: Optional[str] = None
    player_id: Optional[str] = None


class JoinRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=64)
    position: Optional[str] = None
    game_id: Optional[str] = None
    player_id: Optional[str] = None


class RoomVisibilityRequest(BaseModel):
    game_id: Optional[str] = None
    is_public: Optional[bool] = None


class LeaveRequest(BaseModel):
    player_id: Optional[str] = None
    game_id: Optional[str] = None


class InviteRequest(BaseModel):
    friend_uid: str
    position: str


class DeclineInviteRequest(BaseModel):
    position: str


@router.post("/api/room/{game_id}/invite", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def invite_friend(game_id: str, data: InviteRequest, authorization: str = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    user_info = identify_user(authorization)
    if not user_info:
        return error("Unauthorized", 401)
    
    uid = user_info.get("uid")
    requester_name = (user_info.get("name") or "").strip()
    inviter_name = user_info.get("name") or "A friend"

    # Diagnostic logging for 403 issues
    logger = logging.getLogger("virtual_engine.invite")
    member_player_ids = [getattr(p, "player_id", None) for p in (game.players or [])]
    member_player_names = [getattr(p, "player_name", None) for p in (game.players or [])]
    creator_player = game.get_player(game.creator_id) if game.creator_id else None
    creator_name = getattr(creator_player, "player_name", None)
    logger.info(
        "Invite Attempt: game=%s, uid=%s, requester_name=%s, creator_id=%s, creator_name=%s, members=%s, member_names=%s",
        game_id,
        uid,
        requester_name,
        game.creator_id,
        creator_name,
        member_player_ids,
        member_player_names,
    )

    # Validation: user must be the room host OR already present as a member.
    # NOTE: different parts of the codebase may use different identifiers (e.g. uid vs player_id).
    # We accept either matching player_id OR matching the host creator_id.
    # Some clients may re-authenticate with a different token while keeping the same room identity,
    # so we also allow matching by the display name currently used in the room.
    uid_str = str(uid) if uid is not None else None
    creator_str = str(game.creator_id) if game.creator_id is not None else None

    is_host = creator_str is not None and uid_str is not None and creator_str == uid_str
    is_in_game = False
    if uid_str is not None:
        for p in game.players or []:
            p_id = getattr(p, "player_id", None)
            if p_id is not None and str(p_id) == uid_str:
                is_in_game = True
                break

    name_matches_host = bool(requester_name and creator_name and requester_name == creator_name)
    name_matches_member = bool(
        requester_name
        and any(
            requester_name == str(member_name)
            for member_name in member_player_names
            if member_name is not None
        )
    )

    # If we reach here and neither matches, reject.
    if not is_host and not is_in_game and not name_matches_host and not name_matches_member:
        logger.warning(
            "Invite Forbidden: game=%s requester_uid=%s requester_name=%s creator_id=%s creator_name=%s is_in_game=%s name_matches_host=%s name_matches_member=%s member_player_ids=%s member_names=%s",
            game_id,
            uid,
            requester_name,
            game.creator_id,
            creator_name,
            is_in_game,
            name_matches_host,
            name_matches_member,
            member_player_ids,
            member_player_names,
        )
        return error(
            f"Forbidden: requester {uid} is not host {game.creator_id} or in room",
            403,
        )


    # Reserve seat and store invitation in Redis
    success, msg = game.reserve_seat(data.friend_uid, data.position)
    if not success:
        return error(msg, 400)

    from shared.redis_client import get_redis
    r = get_redis()
    invite_key = f"invites:{data.friend_uid}"
    invite_data = {
        "game_id": game_id,
        "inviter_name": inviter_name,
        "position": data.position,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    r.lpush(invite_key, json.dumps(invite_data))
    r.expire(invite_key, 300) # Invites expire in 5 minutes

    return {"success": True, "message": f"Invitation sent to {data.friend_uid}"}


@router.post("/api/room/{game_id}/invite/decline", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def decline_invite(game_id: str, data: DeclineInviteRequest, authorization: str = Header(default=None)):
    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    user_info = identify_user(authorization)
    if not user_info:
        return error("Unauthorized", 401)

    uid = user_info.get("uid")
    requester_name = (user_info.get("name") or "").strip()

    logger.info(
        "Decline Invite Attempt: game=%s, uid=%s, requester_name=%s, position=%s",
        game_id,
        uid,
        requester_name,
        data.position,
    )

    success, msg = game.release_reserved_seat(uid, data.position)
    if not success:
        return error(msg, 400)

    return {"success": True, "message": f"Invitation declined for position {data.position}"}


@router.get("/api/invites", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_invites(authorization: str = Header(default=None)):
    user_info = identify_user(authorization)
    if not user_info:
        return error("Unauthorized", 401)
    
    uid = user_info.get("uid")

    from shared.redis_client import get_redis
    r = get_redis()
    invite_key = f"invites:{uid}"
    
    invites_raw = r.lrange(invite_key, 0, -1)
    r.delete(invite_key) # Clear after reading
    
    invites = [json.loads(i) for i in invites_raw]
    
    return {"success": True, "invites": invites}


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

        game_state = game.get_state() or {}
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
def create_room_endpoint(data: CreateRoomRequest = Body(default_factory=dict), authorization: str = Header(default=None)):
    user_info = identify_user(authorization)
    
    name = data.name.strip() if data.name else user_info.get("name") or ""
    position = data.position
    player_id_input = data.player_id or user_info.get("uid")
    
    logger.info(f"Create Room Attempt: name={name}, player_id_input={player_id_input}, data_player_id={data.player_id}, user_info_uid={user_info.get('uid')}")

    if name:
        success, message, game_id, player_id = manager.create_room_with_host(name, position, player_id=player_id_input)
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
def create_game(data: CreateGameRequest = Body(...), authorization: str = Header(default=None)):
    user_info = identify_user(authorization)
    
    name = data.name.strip() if data.name else user_info.get("name") or ""
    position = data.position
    player_id_input = data.player_id or user_info.get("uid")

    success, message, game_id, player_id = manager.create_game(name, position, player_id=player_id_input)
    return {
        "success": success,
        "message": message,
        "game_id": game_id,
        "player_id": player_id,
    }


@router.post("/api/join", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def join_game(data: JoinRequest = Body(...), authorization: str | None = Header(default=None)):
    user_info = identify_user(authorization)
    
    name = data.name.strip() if data.name else user_info.get("name") or ""
    position = data.position
    game_id = data.game_id or manager.default_game_id
    player_id_input = data.player_id or user_info.get("uid")

    logger.info(f"Join Attempt: game={game_id}, name={name}, player_id_input={player_id_input}, data_player_id={data.player_id}, user_info_uid={user_info.get('uid')}")

    game = manager.get_game(game_id)
    if not game:
        return error(f"Game {game_id} not found", 404)

    success, message, player_id = game.add_player(name, position, player_id=player_id_input)
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
