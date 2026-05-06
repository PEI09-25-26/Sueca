from fastapi import FastAPI, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from shared.firebase_client import (
    add_friend,
    get_user,
    get_friends,
    remove_friend,
    add_friend_request,
    get_incoming_friend_requests,
    accept_friend_request,
    reject_friend_request,
)
from shared.ratelimit import rate_limit_dependency

app = FastAPI(title="Sueca Friends Service")


class FriendRequest(BaseModel):
    user: str
    friend: str


class FriendRequestAction(BaseModel):
    request_id: str | None = None
    user: str | None = None
    friend: str | None = None


def _extract_friend_request(data: dict) -> tuple[str, str]:
    from_user = (data.get("user") or data.get("from_uid") or data.get("fromUid") or "").strip()
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
def get_friends_route(user: str | None = None, uid: str | None = None):
    user_id = user or uid
    if not user_id:
        raise HTTPException(status_code=400, detail="user or uid required")

    friend_ids = get_friends(user_id)
    friends_payload = []
    for friend_id in friend_ids:
        friend_doc = get_user(friend_id)
        if not friend_doc:
            continue
        friends_payload.append({
            "uid": friend_id,
            "username": friend_doc.get("username", ""),
            "email": friend_doc.get("email", ""),
            "emailVerified": bool(friend_doc.get("emailVerified", False)),
            "description": friend_doc.get("description", ""),
            "photoURL": friend_doc.get("photoURL", ""),
            "bannerURL": friend_doc.get("bannerURL", ""),
            "createdAt": friend_doc.get("createdAt") or friend_doc.get("created_at") or "",
            "updatedAt": friend_doc.get("updatedAt") or friend_doc.get("updated_at") or "",
            "lastLoginAt": friend_doc.get("lastLoginAt"),
            "privacy": friend_doc.get("privacy", "public"),
            "friendsCount": len(get_friends(friend_id)),
            "status": friend_doc.get("status", "online"),
            "friendCode": friend_doc.get("friendCode"),
        })

    return {"success": True, "friends": friends_payload, "count": len(friends_payload)}

@app.get("/friends/get_code", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def get_friend_code(user: str | None = None, uid: str | None = None):
    """Retrieves the permanent friend code for a given user."""
    user_id = user or uid
    if not user_id:
        raise HTTPException(status_code=400, detail="user or uid required")

    user_doc = get_user(user_id)
    print(f"get_friend_code: user_id={user_id}, user_doc={user_doc}")
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    friend_code = user_doc.get("friendCode")
    if not friend_code:
        raise HTTPException(status_code=404, detail="Friend code not found for this user")

    return {"code": friend_code}

@app.post("/friends/request", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/request", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def request_friend_route(data: dict = Body(default_factory=dict)):
    from_user, to_user = _extract_friend_request(data)
    ok = add_friend_request(from_user, to_user)
    if not ok:
        return {"success": True, "requested": False, "message": "request already exists"}
    return {"success": True, "requested": True}


@app.get("/friends/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
@app.get("/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def incoming_requests(user: str | None = None, uid: str | None = None):
    user_id = user or uid
    if not user_id:
        raise HTTPException(status_code=400, detail="user or uid required")
    requests = get_incoming_friend_requests(user_id)
    return {"success": True, "requests": requests, "count": len(requests)}


@app.post("/friends/accept", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/accept", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def accept_request(data: dict = Body(default_factory=dict)):
    user, friend = _extract_request_action(data)
    ok = accept_friend_request(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.post("/friends/reject", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
@app.post("/decline", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def reject_request(data: dict = Body(default_factory=dict)):
    user, friend = _extract_request_action(data)
    ok = reject_friend_request(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.delete("/friends", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def remove_friend_route(data: dict = Body(default_factory=dict)):
    user, friend = _extract_friend_request(data)
    ok = remove_friend(user, friend)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"success": True}
