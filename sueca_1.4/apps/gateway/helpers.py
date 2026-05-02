import subprocess
import threading
from pathlib import Path
from typing import Optional

import requests

from shared.contracts import normalize_event, normalize_room_state, to_dict

from . import state


def normalize_mode(mode: Optional[str]) -> str:
    if str(mode).strip().lower() == "physical":
        return "physical"
    return "virtual"


def remember_room_mode(game_id: Optional[str], mode: str):
    if game_id:
        state.room_modes[game_id] = normalize_mode(mode)


def infer_mode_from_payload(payload: dict, default_mode: str) -> str:
    if isinstance(payload, dict) and payload.get("mode"):
        return normalize_mode(payload.get("mode"))
    if isinstance(payload, dict) and payload.get("game_id") in state.room_modes:
        return state.room_modes[payload.get("game_id")]
    return normalize_mode(default_mode)


def ingest_state(payload: dict, source: str, default_mode: str):
    mode = infer_mode_from_payload(payload, default_mode)
    room_state = normalize_room_state(payload, source=source, mode=mode)
    canonical_state = to_dict(room_state)
    game_id = canonical_state.get("game_id")

    state.latest_state_raw = payload
    state.latest_room_state = canonical_state
    if game_id:
        state.latest_state_raw_by_game[game_id] = payload
        state.latest_room_state_by_game[game_id] = canonical_state
    remember_room_mode(game_id, mode)

    if state.FORWARD_TO_FRONTEND:
        def push():
            try:
                state.frontend.send_state(payload)
            except Exception as error:
                print(f"[Middleware] Failed to push state to frontend: {error}")

        threading.Thread(target=push, daemon=True).start()
    return canonical_state


def ingest_event(payload: dict, source: str, default_mode: str):
    mode = infer_mode_from_payload(payload, default_mode)
    envelope = normalize_event(payload, source=source, mode=mode)
    event_payload = to_dict(envelope)
    remember_room_mode(event_payload.get("game_id"), mode)

    if state.FORWARD_TO_FRONTEND:
        def push_event():
            try:
                state.frontend.send_event(event_payload)
            except Exception as error:
                print(f"[Middleware] Failed to push event to frontend: {error}")

        threading.Thread(target=push_event, daemon=True).start()

    return envelope, event_payload


def target_base_for_mode(mode: str) -> str:
    if normalize_mode(mode) == "physical":
        return state.PHYSICAL_ENGINE_URL
    return state.VIRTUAL_ENGINE_URL


def is_service_up(url: str) -> bool:
    try:
        response = requests.get(url, timeout=0.6)
        return response.status_code < 500
    except Exception:
        return False


def start_service(name: str, command: list[str], health_url: str, cwd: Optional[Path] = None):
    if is_service_up(health_url):
        return

    process = subprocess.Popen(
        command,
        cwd=str(cwd or state.ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    state.service_processes[name] = process


def stop_managed_services():
    for name, process in tuple(state.service_processes.items()):
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        finally:
            state.service_processes.pop(name, None)
