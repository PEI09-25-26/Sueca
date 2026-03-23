# Sueca 1.4 Component Purposes

## High-level architecture

Sueca 1.4 is split into 4 main runtime parts:

- Gateway: single entrypoint and router
- Virtual Engine: full digital game logic and bots
- Physical CV: card detection from camera stream
- Physical Game: physical table referee/game state

## Gateway (apps/gateway)

### Purpose

- Central API clients call first
- Routes commands/queries to the correct backend by room mode
- Exposes shared game-facing endpoints
- Coordinates managed startup for dependent services in dev mode

### Key modules

- main.py: FastAPI app bootstrap
- lifecycle.py: startup and service orchestration
- routes/proxy_routes.py: command/query forwarding
- routes/game_routes.py and routes/state_routes.py: shared room/state APIs
- routes/websocket_routes.py: camera/game websocket bridge

## Virtual Engine (apps/virtual_engine)

### Purpose

- Owns game rules for virtual matches
- Handles rooms, joins, teams, turns, rounds, scoring, rematches
- Publishes state and events to MQTT for strict event-driven clients
- Runs bot agents

### Key modules

- api.py: virtual engine API bootstrap
- core/game_core.py: authoritative game state and rules
- routes/room_routes.py: room and lobby endpoints
- routes/player_routes.py: seat changes, bot add, player removal
- routes/gameplay_routes.py: cut, trump, play, reset
- event_publisher.py: high-level event publishing
- clients/client.py: bot-facing client adapter

## Bot Agents (apps/virtual_engine/agents)

### Purpose

- Automated players that join rooms and play by heuristics

### Implementations

- random_agent: random legal card strategy
- weak_agent: simple heuristic strategy

### Shared behavior

- Read state and hand (MQTT-driven)
- Execute actions through virtual engine APIs
- Stay alive across rematches

## Physical CV (apps/physical_engine/cv_service.py)

### Purpose

- Accept camera stream frames
- Detect card rank/suit with confidence
- Push detections to physical game flow

## Physical Game (apps/physical_engine/game_service.py, referee.py)

### Purpose

- Manage physical-table match progression
- Validate and queue physical card inputs
- Keep canonical physical match state

## Shared and integration support

- apps/emqx/mqtt_client.py: MQTT connection and publish helper
- shared/contracts: canonical contract transformation
- scripts/mqtt_end_to_end_probe.py: end-to-end probe for command plus MQTT state flow
- run_automation_tests.py: integration sanity checks
