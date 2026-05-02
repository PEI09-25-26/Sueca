from typing import Annotated, Optional

import logging
import requests
from fastapi import APIRouter, Query

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

    if mode == "virtual":
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
        },
    }
