import os
import subprocess
import threading
import queue
from pathlib import Path
from typing import Optional

import requests
import jwt
from fastapi import Header, HTTPException

from shared.contracts import normalize_event, normalize_room_state, to_dict

from . import state
from apps.virtual_engine.session import session_manager


class _ForwardDispatcher:
    """Bounded async forwarder for frontend state/event fan-out."""

    def __init__(self, workers: int = 2, queue_size: int = 512):
        self._queue: queue.Queue[tuple[str, dict]] = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []
        for index in range(max(1, workers)):
            worker = threading.Thread(target=self._run, daemon=True, name=f"gateway-forward-{index}")
            worker.start()
            self._workers.append(worker)

    def submit(self, kind: str, payload: dict):
        try:
            self._queue.put_nowait((kind, payload))
        except queue.Full:
            print(f"[Middleware] Dropping {kind} payload because forwarding queue is full")

    def _run(self):
        while not self._stop.is_set():
            try:
                kind, payload = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                if kind == "state":
                    state.frontend.send_state(payload)

                    # Also broadcast to active mobile WebSockets
                    game_id = payload.get("game_id")
                    if game_id and game_id in state.active_connections:
                        ws = state.active_connections[game_id]
                        # Use main loop to send as this is a separate thread
                        if state.main_loop:
                            asyncio.run_coroutine_threadsafe(
                                ws.send_json({"success": True, "game_state": payload}),
                                state.main_loop
                            )
                else:
                    state.frontend.send_event(payload)
            except Exception as error:
                print(f"[Middleware] Failed to push {kind} to frontend: {error}")
            finally:
                self._queue.task_done()


FORWARD_DISPATCHER = _ForwardDispatcher()


def normalize_mode(mode: Optional[str]) -> str:
    mode_lower = str(mode).strip().lower()
    if mode_lower == "physical":
        return "physical"
    if mode_lower == "hybrid":
        return "hybrid"
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
        FORWARD_DISPATCHER.submit("state", payload)
    return canonical_state


def ingest_event(payload: dict, source: str, default_mode: str):
    mode = infer_mode_from_payload(payload, default_mode)
    envelope = normalize_event(payload, source=source, mode=mode)
    event_payload = to_dict(envelope)
    remember_room_mode(event_payload.get("game_id"), mode)

    if state.FORWARD_TO_FRONTEND:
        FORWARD_DISPATCHER.submit("event", event_payload)

    return envelope, event_payload


def target_base_for_mode(mode: str) -> str:
    normalized = normalize_mode(mode)
    if normalized == "hybrid":
        return state.HYBRID_ENGINE_URL
    if normalized == "physical":
        return state.PHYSICAL_ENGINE_URL
    return state.VIRTUAL_ENGINE_URL


def is_service_up(url: str) -> bool:
    try:
        response = state.INTERNAL_HTTP.get(url, timeout=0.6)
        return response.status_code < 500
    except Exception:
        return False


def start_service(name: str, command: list[str], health_url: str, cwd: Optional[Path] = None):
    if is_service_up(health_url):
        return

    # Ensure ROOT_DIR is in PYTHONPATH so absolute imports like 'apps.emqx...' work
    env = os.environ.copy()
    root_str = str(state.ROOT_DIR)
    current_pythonpath = env.get("PYTHONPATH", "")
    if current_pythonpath:
        env["PYTHONPATH"] = f"{root_str}{os.pathsep}{current_pythonpath}"
    else:
        env["PYTHONPATH"] = root_str

    process = subprocess.Popen(
        command,
        cwd=str(cwd or state.ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
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


def require_any_token(authorization: str | None = Header(default=None)):
    """
    FastAPI dependency that validates either a local session token or a global JWT.
    Returns the decoded payload if valid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing authorization header")

    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    else:
        token = authorization.strip()

    if not token:
        raise HTTPException(status_code=401, detail="empty authorization token")

    # 1. Try local session manager (guest or virtual engine sessions)
    session_data = session_manager.validate_token(token)
    if session_data:
        return session_data

    # 2. Try global secret (Firebase or main auth service)
    secret = os.getenv("SECRET_KEY") or os.getenv("SUECA_JWT_SECRET")
    if secret:
        try:
            # We use HS256 as standard across internal services
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.PyJWTError:
            pass

    raise HTTPException(status_code=401, detail="invalid or expired authorization token")
