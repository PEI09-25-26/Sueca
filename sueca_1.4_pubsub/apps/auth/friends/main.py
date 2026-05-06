from fastapi import FastAPI, HTTPException, Depends, Query
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
    return {"friends": get_friends(user_id)}

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
def request_friend_route(req: FriendRequest):
    ok = add_friend_request(req.user, req.friend)
    if not ok:
        raise HTTPException(status_code=400, detail="request already exists")
    return {"success": True, "requested": True}


@app.get("/friends/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
@app.get("/requests", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def incoming_requests(user: str | None = None, uid: str | None = None):
    user_id = user or uid
    if not user_id:
        raise HTTPException(status_code=400, detail="user or uid required")
    return {"requests": get_incoming_friend_requests(user_id)}


@app.post("/friends/accept", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def accept_request(req: FriendRequest):
    ok = accept_friend_request(req.user, req.friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.post("/friends/reject", dependencies=[Depends(rate_limit_dependency(limit=20, window_seconds=60))])
def reject_request(req: FriendRequest):
    ok = reject_friend_request(req.user, req.friend)
    if not ok:
        raise HTTPException(status_code=404, detail="request not found")
    return {"success": True}


@app.delete("/friends", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def remove_friend_route(req: FriendRequest):
    ok = remove_friend(req.user, req.friend)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"success": True}
