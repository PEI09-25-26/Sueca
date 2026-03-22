import sys
import os
import subprocess
import time
from . import state
from .helpers import start_service, stop_managed_services, is_service_up


EMQX_CONTAINER = "emqx-sueca"
EMQX_HEALTH_URL = "http://127.0.0.1:18083/status"
FORCE_RESTART_ON_STARTUP = os.getenv("SUECA_FORCE_RESTART_SERVICES", "1") == "1"


def _terminate_matching_processes(pattern: str):
    """Terminate any running process matching pattern (best effort)."""
    try:
        found = _run_command(["pgrep", "-f", pattern])
        if found.returncode != 0:
            return
        pids = [pid.strip() for pid in (found.stdout or "").splitlines() if pid.strip()]
        for pid in pids:
            _run_command(["kill", "-TERM", pid])
        time.sleep(0.2)
        for pid in pids:
            still = _run_command(["kill", "-0", pid])
            if still.returncode == 0:
                _run_command(["kill", "-KILL", pid])
    except Exception as error:
        print(f"[MIDDLEWARE] Failed terminating processes for pattern '{pattern}': {error}")


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _ensure_emqx_running() -> bool:
    if is_service_up(EMQX_HEALTH_URL):
        return True

    try:
        docker_bin = _run_command(["which", "docker"])
        if docker_bin.returncode != 0:
            print("[MIDDLEWARE] Docker is not available; EMQX cannot be auto-started.")
            return False

        existing = _run_command(
            ["docker", "ps", "-a", "--filter", f"name=^/{EMQX_CONTAINER}$", "--format", "{{.Names}}"],
        )
        exists = EMQX_CONTAINER in (existing.stdout or "")

        if exists:
            started = _run_command(["docker", "start", EMQX_CONTAINER])
            if started.returncode != 0:
                print(f"[MIDDLEWARE] Failed to start EMQX container '{EMQX_CONTAINER}': {started.stderr.strip()}")
                return False
        else:
            created = _run_command(
                [
                    "docker", "run", "-d",
                    "--name", EMQX_CONTAINER,
                    "--restart", "unless-stopped",
                    "-p", "1883:1883",
                    "-p", "8883:8883",
                    "-p", "8083:8083",
                    "-p", "8084:8084",
                    "-p", "18083:18083",
                    "-e", "EMQX_NAME=sueca-game",
                    "-e", "EMQX_HOST=localhost",
                    "emqx/emqx:5.8.1",
                ],
            )
            if created.returncode != 0:
                print(f"[MIDDLEWARE] Failed to create EMQX container '{EMQX_CONTAINER}': {created.stderr.strip()}")
                return False

        deadline = time.time() + 20
        while time.time() < deadline:
            if is_service_up(EMQX_HEALTH_URL):
                print("[MIDDLEWARE] EMQX broker is healthy on 127.0.0.1:18083")
                return True
            time.sleep(0.3)
        print("[MIDDLEWARE] EMQX did not become healthy in time (expected /status on :18083).")
        return False
    except Exception as error:
        print(f"[MIDDLEWARE] Failed to ensure EMQX is running: {error}")
        return False


def startup_services():
    if not state.AUTOSTART_SERVICES:
        return

    if FORCE_RESTART_ON_STARTUP:
        _terminate_matching_processes("uvicorn apps.virtual_engine.api:app")
        _terminate_matching_processes("uvicorn cv_service:app")
        _terminate_matching_processes("uvicorn game_service:app")

    # Bring the broker up first to avoid losing initial retained state publishes.
    _ensure_emqx_running()

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
    # Keep EMQX running across gateway restarts. Stop it manually only when needed.