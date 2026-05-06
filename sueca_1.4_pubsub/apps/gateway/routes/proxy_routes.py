from typing import Annotated, Optional

import logging
import requests
import json
from fastapi import APIRouter, Query, Request, Response

from .. import state
from ..dto import CommandRequestDTO
from ..helpers import is_service_up, normalize_mode, target_base_for_mode

router = APIRouter()
logger = logging.getLogger(__name__)
APPLICATION_JSON = "application/json"


def _decode_backend_response(response: requests.Response):
    if not response.content:
        return {"success": response.ok}

    try:
        return response.json()
    except ValueError:
        text_body = response.text.strip()
        return {
            "success": response.ok,
            "message": text_body or response.reason or "Backend returned non-JSON payload",
            "raw": text_body,
        }


@router.post("/game/command/{command:path}")
def route_command(command: str, request_data: CommandRequestDTO):
    game_id = request_data.game_id
    mode = request_data.mode or state.room_modes.get(game_id, "virtual")
    mode = normalize_mode(mode)
    target = target_base_for_mode(mode)

    payload = dict(request_data.payload or {})
    if game_id and "game_id" not in payload:
        payload["game_id"] = game_id
    payload.setdefault("mode", mode)

    if mode == "virtual":
        target_url = f"{target}/api/{command}"
    else:
        target_url = f"{target}/{command}"

    try:
        response = state.INTERNAL_HTTP.post(target_url, json=payload, timeout=5)
        data = _decode_backend_response(response)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "mode": mode, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.get("/game/query/{query_path:path}")
def route_query(
    query_path: str,
    game_id: Annotated[Optional[str], Query()] = None,
    mode: Annotated[Optional[str], Query()] = None,
):
    resolved_mode = normalize_mode(mode or state.room_modes.get(game_id, "virtual"))
    target = target_base_for_mode(resolved_mode)

    if resolved_mode == "virtual":
        target_url = f"{target}/api/{query_path}"
    else:
        target_url = f"{target}/{query_path}"

    params = {}
    if game_id:
        params["game_id"] = game_id

    try:
        response = state.INTERNAL_HTTP.get(target_url, params=params, timeout=5)
        data = _decode_backend_response(response)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "mode": resolved_mode, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.post("/stats/game/{game_id:path}")
def route_stats(game_id: str):
    if not game_id:
        return {"success": False, "message": "game_id is required"}
    target = f"{state.STATS_SERVICE_URL.rstrip('/')}/game/{game_id}"
    try:
        response = state.INTERNAL_HTTP.post(target, timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.get("/presence")
def route_presence():
    try:
        response = state.INTERNAL_HTTP.get(f"{state.PRESENCE_SERVICE_URL.rstrip('/')}/status", timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(status_code=502, content=json.dumps({"success": False, "message": str(error)}), media_type=APPLICATION_JSON)


@router.get("/api/status")
def proxy_api_status(request: Request):
    game_id = request.query_params.get("game_id")
    mode = normalize_mode(state.room_modes.get(game_id, "virtual"))
    target = target_base_for_mode(mode)
    target_url = f"{target}/api/status"
    try:
        response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )

@router.get("/api/rooms")
def proxy_api_rooms(request: Request):
    target = target_base_for_mode("virtual")
    target_url = f"{target}/api/rooms"
    try:
        response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.post("/api/create_room")
def proxy_api_create_room(request: Request):
    target = target_base_for_mode("virtual")
    target_url = f"{target}/api/create_room"
    try:
        response = state.INTERNAL_HTTP.post(target_url, timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.post("/api/start")
async def proxy_api_start(request: Request):
    target = target_base_for_mode("virtual")
    target_url = f"{target}/api/start"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else {}
        if isinstance(body, dict) and "roomId" in body and "game_id" not in body:
            body["game_id"] = body.get("roomId")
        response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api_auth(path: str, request: Request):
    target = state.AUTH_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(path: str, request: Request):
    target = state.AUTH_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/api/friends/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api_friends(path: str, request: Request):
    target = state.FRIENDS_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/friends/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_friends(path: str, request: Request):
    target = state.FRIENDS_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/api/agents/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api_agents(path: str, request: Request):
    target = state.AGENTS_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )


@router.api_route("/agents/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_agents(path: str, request: Request):
    target = state.AGENTS_SERVICE_URL.rstrip("/")
    target_url = f"{target}/{path}"
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith(APPLICATION_JSON) else None
        method = request.method.upper()
        if method == "POST":
            response = state.INTERNAL_HTTP.post(target_url, json=body, timeout=5)
        elif method == "PUT":
            response = state.INTERNAL_HTTP.put(target_url, json=body, timeout=5)
        elif method == "DELETE":
            response = state.INTERNAL_HTTP.delete(target_url, json=body, timeout=5)
        else:
            response = state.INTERNAL_HTTP.get(target_url, params=dict(request.query_params), timeout=5)
        return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("Content-Type"))
    except requests.RequestException as error:
        return Response(
            status_code=502,
            content=json.dumps({"success": False, "target": target_url, "message": str(error)}),
            media_type=APPLICATION_JSON,
        )
