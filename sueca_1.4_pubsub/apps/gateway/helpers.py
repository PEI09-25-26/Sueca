import threading
import queue
from typing import Optional

from fastapi import Header, HTTPException, status
import os
import jwt
import logging
from shared.redis_client import is_jti_revoked

from shared.contracts import normalize_event, normalize_room_state, to_dict

from . import state


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
                else:
                    state.frontend.send_event(payload)
            except Exception as error:
                print(f"[Middleware] Failed to push {kind} to frontend: {error}")
            finally:
                self._queue.task_done()


FORWARD_DISPATCHER = _ForwardDispatcher()


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
    if normalize_mode(mode) == "physical":
        return state.PHYSICAL_ENGINE_URL
    return state.VIRTUAL_ENGINE_URL


def is_service_up(url: str) -> bool:
    try:
        response = state.INTERNAL_HTTP.get(url, timeout=0.6)
        return response.status_code < 500
    except Exception:
        return False


def require_control_plane_token(authorization: str | None = Header(default=None)) -> bool:
    """Dependency that enforces a signed service JWT for control-plane actions.

    Expects a Bearer token signed with `SUECA_SERVICE_JWT_SECRET` and containing
    a claim `scope: "control_plane"`. Also checks the token `jti` against the
    Redis denylist to ensure revoked service tokens are rejected.
    """
    logger = logging.getLogger(__name__)
    secret = os.getenv("SUECA_SERVICE_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="server misconfigured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid authorization header")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])  # type: ignore
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service token")

    # ensure scope
    if payload.get("scope") != "control_plane":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient scope")

    # denylist check
    jti = payload.get("jti")
    if jti and is_jti_revoked(jti):
        logger.warning("Rejected revoked service token jti=%s", jti)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service token revoked")

    return True


# start_service / stop_managed_services removed — orchestration should be handled by
# container tooling (docker-compose / k8s) or external process managers.
