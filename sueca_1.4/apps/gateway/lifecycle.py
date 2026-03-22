import sys

from . import state
from .helpers import start_service, stop_managed_services


def startup_services():
    if not state.AUTOSTART_SERVICES:
        return

    start_service(
        "virtual_engine",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.virtual_engine.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "5000",
        ],
        f"{state.VIRTUAL_ENGINE_URL}/api/status",
    )

    physical_dir = state.ROOT_DIR / "apps" / "physical_engine"
    start_service(
        "physical_cv",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "cv_service:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
            "--app-dir",
            str(physical_dir),
        ],
        f"{state.CV_SERVICE_URL}/health",
    )

    start_service(
        "physical_game",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "game_service:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
            "--app-dir",
            str(physical_dir),
        ],
        f"{state.PHYSICAL_ENGINE_URL}/state",
    )


def shutdown_services():
    stop_managed_services()
