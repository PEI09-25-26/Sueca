# Sueca 1.4

Service-oriented architecture with a single middleware entrypoint.

## Run One Server

From `sueca_1.4` run:

`uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000`

What happens:

- Gateway starts as the main middleware API.
- Dependent services are auto-started in dev mode:
	- virtual engine (`apps.virtual_engine.api`) on 5000
	- physical CV service on 8001
	- physical game service on 8002

To disable auto-start and run services manually:

`SUECA_AUTOSTART_SERVICES=0 uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000`

## Middleware Routing by Game Type

The middleware decides which service to call based on room/game mode:

- `virtual` -> virtual engine
- `physical` -> physical engine

Main endpoints:

- `POST /game/room_mode/{game_id}` set room mode
- `GET /game/room_mode/{game_id}` get room mode
- `POST /game/command/{command}` command routing by mode
- `GET /system/services` health/status of managed services

## Current Domains

- `apps/virtual_engine`
- `apps/physical_engine`
- `apps/gateway`
- `shared/contracts`
- `shared/security`
- `shared/messaging`
- `shared/config`
- `docs`

## Folder Organization

### Gateway

- `apps/gateway/main.py` (HTTP/WS entrypoint)
- `apps/gateway/routes/` (state, proxy, game and websocket routes)
- `apps/gateway/lifecycle.py` (service startup/shutdown)
- `apps/gateway/helpers.py` and `apps/gateway/state.py` (shared gateway internals)
- `apps/gateway/clients/` (integration clients)
- `apps/gateway/schemas/` (gateway DTO/dataclass models)

### Virtual Engine

- `apps/virtual_engine/api.py` (FastAPI entrypoint)
- `apps/virtual_engine/core/` (game core logic)
- `apps/virtual_engine/routes/` (room/player/gameplay route modules)
- `apps/virtual_engine/agents/random_agent/` (bot logic)
- `apps/virtual_engine/agents/weak_agent/` (heuristic weak bot)
- `apps/virtual_engine/clients/` (CLI/game client layer)

### Current Docs

- `docs/ENDPOINTS.md` (complete endpoint catalog)
- `docs/SUECA_1_4_STATUS_AND_ROADMAP.md` (what is done and what is missing)
- `docs/INTEGRATION-CHECKLIST.md` (integration readiness checklist)

### Physical Engine

- `apps/physical_engine/core/` (physical game and CV core logic)
- `apps/physical_engine/routes/` (physical HTTP route layer)
- `apps/physical_engine/cv/` (computer vision classifier/detector modules)

## Automated Testing

Run the automated suite with one command:

`python3 run_automation_tests.py`

The suite checks:

- gateway routing and proxy behavior
- virtual engine endpoint flows
- physical game/CV service basic endpoints

If dependencies are not installed in your current interpreter, install them first:

`python3 -m pip install -r requirements.txt`

If you keep dependencies in an external virtual environment, run with that interpreter:

`/path/to/your/venv/bin/python run_automation_tests.py`

Or keep your usual command and let the runner re-exec automatically:

`SUECA_TEST_PYTHON=/path/to/your/venv/bin/python python3 run_automation_tests.py`
