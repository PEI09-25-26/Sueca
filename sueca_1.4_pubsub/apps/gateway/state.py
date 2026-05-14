import os
import subprocess
from pathlib import Path
from typing import Any

import requests
import websockets

from .clients import BackendClient, FrontendClient
from .schemas import CardDetection
from shared.config import SERVICES


ROOT_DIR = Path(__file__).resolve().parents[2]
AUTOSTART_SERVICES = os.getenv("SUECA_AUTOSTART_SERVICES", "1") == "1"
service_processes: dict[str, subprocess.Popen] = {}

backend = BackendClient(base_url=SERVICES.physical_engine_url)
frontend = FrontendClient(base_url=SERVICES.frontend_url)

latest_state_raw: dict = {}
latest_room_state: dict = {}
latest_state_raw_by_game: dict[str, dict] = {}
latest_room_state_by_game: dict[str, dict] = {}
room_modes: dict[str, str] = {}

CV_SERVICE_URL = SERVICES.cv_service_url
CV_SERVICE_WS_URL = SERVICES.cv_service_ws_url
GAME_SERVICE_URL = SERVICES.physical_engine_url
VIRTUAL_ENGINE_URL = SERVICES.virtual_engine_url
PHYSICAL_ENGINE_URL = SERVICES.physical_engine_url
FORWARD_TO_FRONTEND = SERVICES.frontend_url.rstrip("/") != SERVICES.gateway_url.rstrip("/")

active_connections: dict[str, Any] = {}
cv_connections: dict[str, websockets.WebSocketClientProtocol] = {}

SUIT_SYMBOLS = {
    "Clubs": "♣",
    "Diamonds": "♦",
    "Hearts": "♥",
    "Spades": "♠",
}

INTERNAL_HTTP = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=128)
INTERNAL_HTTP.mount("http://", _adapter)
INTERNAL_HTTP.mount("https://", _adapter)


__all__ = [
    "AUTOSTART_SERVICES",
    "ROOT_DIR",
    "service_processes",
    "backend",
    "frontend",
    "latest_state_raw",
    "latest_room_state",
    "latest_state_raw_by_game",
    "latest_room_state_by_game",
    "room_modes",
    "CV_SERVICE_URL",
    "CV_SERVICE_WS_URL",
    "GAME_SERVICE_URL",
    "VIRTUAL_ENGINE_URL",
    "PHYSICAL_ENGINE_URL",
    "FORWARD_TO_FRONTEND",
    "active_connections",
    "cv_connections",
    "SUIT_SYMBOLS",
    "CardDetection",
    "INTERNAL_HTTP",
]
