from fastapi import FastAPI, HTTPException, Depends, Body, Query
from pydantic import BaseModel
from shared.auth import get_authenticated_uid
from shared.firebase_client import (
    get_user,
    get_friends,
    get_player_stats,
    remove_friend,
    add_friend_request,
    get_incoming_friend_requests,
    accept_friend_request,
    reject_friend_request,
)
from shared.ratelimit import rate_limit_dependency

app = FastAPI(title="Sueca Friends Service")

from shared.logging_config import setup_logging, correlation_id_from_request, set_correlation_id, clear_correlation_id
from fastapi import Request

setup_logging()


@app.middleware("http")
async def _add_cid(request: Request, call_next):
    cid = correlation_id_from_request(request)
    request.state.correlation_id = cid
    set_correlation_id(cid)
    try:
        resp = await call_next(request)
        resp.headers['X-Correlation-ID'] = cid
        return resp
    finally:
        clear_correlation_id()


class FriendRequest(BaseModel):
    user: str | None = None
    uid: str | None = None
    from_uid: str | None = None
    fromUid: str | None = None
    friend: str | None = None
    to_uid: str | None = None
    toUid: str | None = None


class FriendRequestAction(BaseModel):
    request_id: str | None = None
    requestId: str | None = None
    user: str | None = None
    uid: str | None = None
    friend: str | None = None
    from_uid: str | None = None
    fromUid: str | None = None


def _extract_friend_request(data: dict) -> tuple[str, str]:
    from_user = (data.get("user") or data.get("uid") or data.get("from_uid") or data.get("fromUid") or "").strip()
    to_user = (data.get("friend") or data.get("to_uid") or data.get("toUid") or "").strip()
    if not from_user or not to_user:
        raise HTTPException(status_code=422, detail="user/friend or from_uid/to_uid required")
    return from_user, to_user


def _extract_request_action(data: dict) -> tuple[str, str]:
    request_id = (data.get("request_id") or data.get("requestId") or "").strip()
    user = (data.get("user") or data.get("uid") or "").strip()
    friend = (data.get("friend") or data.get("from_uid") or data.get("fromUid") or "").strip()

    if request_id:
        if ":" in request_id:
            user_part, friend_part = request_id.split(":", 1)
            user_part = user_part.strip()
            friend_part = friend_part.strip()
            if user_part and friend_part:
                return user_part, friend_part
        raise HTTPException(status_code=422, detail="invalid request_id")

    if user and friend:
        return user, friend

    raise HTTPException(status_code=422, detail="request_id or user/friend required")


@app.get("/health")
def health():
    return {"healthy": True}


@app.get("/friends", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
@app.get("/friends/list", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
@app.get("/list", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def get_friends_route(
    user: str | None = None,
    uid: str | None = None,
    online_only: bool = Query(default=False),
    authenticated_uid: str = Depends(get_authenticated_uid),
):
    user_id = user or uid or authenticated_uid
    if user_id != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")

    friend_ids = get_friends(user_id)
    friends_payload = []
    for friend_id in friend_ids:
        friend_doc = get_user(friend_id)
        if not friend_doc:
            continue
        
        status = friend_doc.get("status", "offline")
        if online_only and status == "offline":
            continue

        friend_code = friend_doc.get("friendCode") or ""
        player_stats = get_player_stats(friend_code) if friend_code else None

        stats_payload = {
            "player_id": friend_code,
            "games_played": int((player_stats or {}).get("games_played", 0) or 0),
            "wins": int((player_stats or {}).get("wins", 0) or 0),
            "losses": int((player_stats or {}).get("losses", 0) or 0),
            "draws": int((player_stats or {}).get("draws", 0) or 0),
        }

        friends_payload.append({
            "uid": friend_id,
            "username": friend_doc.get("username", ""),
            "email": "",
            "emailVerified": bool(friend_doc.get("emailVerified", False)),
            "description": friend_doc.get("description", ""),
            "photoURL": friend_doc.get("photoURL", ""),
            "bannerURL": friend_doc.get("bannerURL", ""),
            "createdAt": friend_doc.get("createdAt") or friend_doc.get("created_at") or "",
            "updatedAt": friend_doc.get("updatedAt") or friend_doc.get("updated_at") or "",
            "lastLoginAt": friend_doc.get("lastLoginAt"),
            "privacy": friend_doc.get("privacy", "public"),
            "friendsCount": len(get_friends(friend_id)),
            "status": status,
            "friendCode": friend_code,
            "stats": stats_payload,
        })

    return {"success": True, "friends": friends_payload, "count": len(friends_payload)}

@app.get("/friends/get_code", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_friend_code(
    user: str | None = None,
    uid: str | None = None,
    authenticated_uid: str = Depends(get_authenticated_uid),
):
    """Retrieves the permanent friend code for a given user."""
    user_id = user or uid or authenticated_uid
    if user_id != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")

    user_doc = get_user(user_id)
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    friend_code = user_doc.get("friendCode")
    if not friend_code:
        raise HTTPException(status_code=404, detail="Friend code not found for this user")

    return {"code": friend_code}

@app.post("/friends/request", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/request", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def request_friend_route(data: FriendRequest = Body(default_factory=dict), authenticated_uid: str = Depends(get_authenticated_uid)):
    payload = data.dict()
    _, to_user = _extract_friend_request(payload)
    from_user = authenticated_uid
    if from_user == to_user:
        raise HTTPException(status_code=400, detail="cannot friend yourself")
    ok = add_friend_request(from_user, to_user)
    if not ok:
        # Check if already friends
        friends = get_friends(from_user)
        if to_user in friends:
            return {"success": True, "requested": False, "message": "You are already friends"}
        return {"success": True, "requested": False, "message": "request already exists"}
    return {"success": True, "requested": True, "message": "Friend request sent"}


@app.get("/friends/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
@app.get("/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def incoming_requests(
    user: str | None = None,
    uid: str | None = None,
    authenticated_uid: str = Depends(get_authenticated_uid),
):
    user_id = user or uid or authenticated_uid
    if user_id != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")
    requests = get_incoming_friend_requests(user_id)
    return {"success": True, "requests": requests, "count": len(requests)}


@app.post("/friends/accept", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/accept", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def accept_request(data: FriendRequestAction = Body(default_factory=dict), authenticated_uid: str = Depends(get_authenticated_uid)):
    payload = data.dict()
    user, friend = _extract_request_action(payload)
    if user != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")
    ok = accept_friend_request(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.post("/friends/reject", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/decline", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def reject_request(data: FriendRequestAction = Body(default_factory=dict), authenticated_uid: str = Depends(get_authenticated_uid)):
    payload = data.dict()
    user, friend = _extract_request_action(payload)
    if user != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")
    ok = reject_friend_request(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.delete("/friends", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def remove_friend_route(data: FriendRequest = Body(default_factory=dict), authenticated_uid: str = Depends(get_authenticated_uid)):
    payload = data.dict()
    user, friend = _extract_friend_request(payload)
    if user != authenticated_uid:
        raise HTTPException(status_code=403, detail="forbidden")
    ok = remove_friend(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"success": True}
