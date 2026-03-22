# Sueca 1.4 Important Commands

## Run Gateway (recommended entrypoint)

Use this from the Sueca workspace root:

```bash
cd sueca_1.4
export PYTHONPATH="$PWD"
python3 -m uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8080
```

## Run Virtual Engine directly

```bash
cd sueca_1.4
export PYTHONPATH="$PWD"
python3 -m uvicorn apps.virtual_engine.api:app --host 127.0.0.1 --port 5000
```

## Run Physical Game service directly

```bash
cd sueca_1.4
export PYTHONPATH="$PWD"
python3 -m uvicorn apps.physical_engine.game_service:app --host 127.0.0.1 --port 8002
```

## Run Physical CV service directly

```bash
cd sueca_1.4
export PYTHONPATH="$PWD"
python3 -m uvicorn apps.physical_engine.cv_service:app --host 127.0.0.1 --port 8001
```

## Run CLI client

```bash
cd sueca_1.4
python3 client.py
```

## Compile-check important files quickly

```bash
cd sueca_1.4
python3 -m py_compile client.py apps/virtual_engine/core/game_core.py apps/virtual_engine/agents/random_agent/random_agent.py apps/virtual_engine/agents/weak_agent/weak_agent.py
```

## Run automated tests

```bash
cd sueca_1.4
python3 run_automation_tests.py
```

## Optional: activate virtual environment first

If you use a virtual environment, activate it before running the commands above:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

## Useful bot commands inside lobby

- Add random bot to first free slot: bot mike
- Add weak bot to first free slot: bot mike as weak
- Add weak bot to specific position: bot south mike as weak
- Add weak bot by slot number: bot 2 mike as weak
- Change your seat: position south
- Show command help: help
