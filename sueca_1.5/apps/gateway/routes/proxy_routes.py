from typing import Annotated, Optional

import logging
import requests
from fastapi import APIRouter, Query, Request

from .. import state
from ..dto import CommandRequestDTO
from ..helpers import is_service_up, normalize_mode, target_base_for_mode


router = APIRouter()
logger = logging.getLogger(__name__)


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

    if mode in ("virtual", "hybrid"):
        target_url = f"{target}/api/{command}"
    else:
        target_url = f"{target}/{command}"

    try:
        response = state.INTERNAL_HTTP.post(target_url, json=payload, timeout=5)
        data = _decode_backend_response(response)
        backend_success = response.ok
        if isinstance(data, dict) and "success" in data:
            backend_success = bool(data.get("success"))

        if response.ok and not backend_success:
            logger.warning("Command %s returned HTTP %s but backend success=false: %s", command, response.status_code, data)

        if backend_success and isinstance(data, dict):
            resolved_game_id = data.get("game_id") or data.get("room_id") or game_id
            if resolved_game_id:
                state.room_modes[resolved_game_id] = mode

        return {
            "success": backend_success,
            "http_success": response.ok,
            "http_status": response.status_code,
            "mode": mode,
            "target": target_url,
            "response": data,
        }
    except requests.RequestException as error:
        return {
            "success": False,
            "mode": mode,
            "target": target_url,
            "message": str(error),
        }


@router.get("/game/query/{query_path:path}")
def route_query(
    query_path: str,
    game_id: Annotated[Optional[str], Query()] = None,
    mode: Annotated[Optional[str], Query()] = None,
):
    resolved_mode = normalize_mode(mode or state.room_modes.get(game_id, "virtual"))
    target = target_base_for_mode(resolved_mode)

    if resolved_mode in ("virtual", "hybrid"):
        target_url = f"{target}/api/{query_path}"
    else:
        target_url = f"{target}/{query_path}"

    params = {}
    if game_id:
        params["game_id"] = game_id

    try:
        response = state.INTERNAL_HTTP.get(target_url, params=params, timeout=5)
        data = _decode_backend_response(response)
        backend_success = response.ok
        if isinstance(data, dict) and "success" in data:
            backend_success = bool(data.get("success"))

        return {
            "success": backend_success,
            "http_success": response.ok,
            "http_status": response.status_code,
            "mode": resolved_mode,
            "target": target_url,
            "response": data,
        }
    except requests.RequestException as error:
        return {
            "success": False,
            "mode": resolved_mode,
            "target": target_url,
            "message": str(error),
        }



# Backwards-compatible proxy: forward legacy /api/* requests to the right engine.
@router.post("/api/{api_path:path}")
def proxy_api_post(api_path: str, request_data: dict = None):
    """Simple POST proxy for legacy clients calling /api/* on the public host."""
    mode = "hybrid" if api_path.startswith("hybrid/") else "virtual"
    target = f"{target_base_for_mode(mode)}/api/{api_path}"
    try:
        response = state.INTERNAL_HTTP.post(target, json=request_data or {}, timeout=5)
        try:
            data = response.json()
        except ValueError:
            data = {"success": response.ok, "raw": response.text}

        return {
            "success": response.ok,
            "http_status": response.status_code,
            "mode": mode,
            "target": target,
            "response": data,
        }
    except requests.RequestException as error:
        return {"success": False, "target": target, "message": str(error)}


@router.get("/api/{api_path:path}")
def proxy_api_get(api_path: str, request: Request):
    """Simple GET proxy for legacy clients calling /api/* on the public host."""
    mode = "hybrid" if api_path.startswith("hybrid/") else "virtual"
    target = f"{target_base_for_mode(mode)}/api/{api_path}"
    try:
        response = state.INTERNAL_HTTP.get(target, params=dict(request.query_params), timeout=5)
        try:
            data = response.json()
        except ValueError:
            data = {"success": response.ok, "raw": response.text}

        return {
            "success": response.ok,
            "http_status": response.status_code,
            "mode": mode,
            "target": target,
            "response": data,
        }
    except requests.RequestException as error:
        return {"success": False, "target": target, "message": str(error)}


@router.get("/system/services")
def service_status():
    return {
        "autostart": state.AUTOSTART_SERVICES,
        "services": {
            "virtual_engine": {
                "url": state.VIRTUAL_ENGINE_URL,
                "healthy": is_service_up(f"{state.VIRTUAL_ENGINE_URL}/api/status"),
                "managed": "virtual_engine" in state.service_processes,
            },
            "physical_cv": {
                "url": state.CV_SERVICE_URL,
                "healthy": is_service_up(f"{state.CV_SERVICE_URL}/health"),
                "managed": "physical_cv" in state.service_processes,
            },
            "physical_game": {
                "url": state.PHYSICAL_ENGINE_URL,
                "healthy": is_service_up(f"{state.PHYSICAL_ENGINE_URL}/state"),
                "managed": "physical_game" in state.service_processes,
            },
            "hybrid_engine": {
                "url": state.HYBRID_ENGINE_URL,
                "healthy": is_service_up(f"{state.HYBRID_ENGINE_URL}/health"),
                "managed": "hybrid_engine" in state.service_processes,
            },
        },
    }
