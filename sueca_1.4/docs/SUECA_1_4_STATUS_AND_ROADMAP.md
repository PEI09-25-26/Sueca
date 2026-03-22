# Sueca 1.4 Status and Roadmap

This document describes the current state of Sueca 1.4, what is already implemented, what is still missing, and what frontend changes are required to fully adapt.

## 1. Current Architecture

## 1.1 Gateway (single integration entrypoint)

- Path: apps/gateway
- Role:
  - receives normalized state/events
  - routes commands and queries by game mode (virtual/physical)
  - orchestrates dependent services in local developer mode
- Main external API surface:
  - /game/state, /game/event
  - /game/room_mode/{game_id}
  - /game/command/{command:path}
  - /game/query/{query_path:path}
  - /system/services
  - /ws/camera/{game_id}

## 1.2 Virtual Engine

- Path: apps/virtual_engine
- Runtime: FastAPI
- Contains:
  - room/match lifecycle
  - deck cut + trump selection + trick rounds
  - room history and match points
  - bot registration and management
- Route organization:
  - routes/room_routes.py
  - routes/player_routes.py
  - routes/gameplay_routes.py
- Bot agents:
  - random_agent
  - weak_agent

## 1.3 Physical Engine

- Path: apps/physical_engine
- Runtime: split services
  - game service (card referee logic)
  - CV service (detection/classification stream)
- Contains:
  - CV WebSocket ingestion and detection flow
  - physical game-state endpoints

## 1.4 Shared Layer

- shared/contracts:
  - canonical room and event schemas
  - normalizers for engine-specific payloads
- shared/config/services.py:
  - centralized service URLs

## 2. YOLO Model and CV Classifier Status

Model artifacts currently in workspace:

- DataSet_Creator/runs/classify/sueca_cards_classifier/weights/best.pt
- DataSet_Creator/yolo11n.pt
- DataSet_Creator/yolov8n-cls.pt
- ComputerVision_1.0/runs/detect/train/weights/best.pt
- ComputerVision_1.0/runs/detect/train2/weights/best.pt

Important runtime note:

- apps/physical_engine/core/cv_core.py expects model at ./runs/classify/sueca_cards_classifier/weights/best.pt relative to physical-engine service runtime.
- If not present there, CV still works in detection-only mode (classifier disabled).

## 3. What Is Done

- Monolithic gateway entrypoint split into modular files (state/helpers/lifecycle/routes).
- Virtual engine moved to FastAPI and organized by route domain.
- Physical engine organized into core + routes + service entrypoints.
- Canonical contract normalization path implemented in shared/contracts.
- Automation test runner exists and passes.
- Weak agent integrated into Sueca 1.4 bot factory.

## 4. What Is Missing / To Do

## 4.1 HTTPS and security hardening

Not fully implemented yet:

- TLS termination strategy for all external traffic (reverse proxy/ingress).
- Strict transport and secure headers policy.
- Auth/session binding for gameplay command ownership checks.
- Explicit authorization guards (room membership + turn ownership).

## 4.2 Message broker integration

Not implemented yet:

- publish/subscribe transport for state/events (replacing polling where needed).
- topic naming strategy and adapters for producer/consumer services.
- durable event delivery and reconnection strategy.

## 4.3 Frontend adaptation completion

Partially done, still required:

- Frontend must call only gateway endpoints, never engines directly.
- Frontend should consume canonical event/state envelope from gateway.
- Frontend should stop relying on engine-specific payload fields where canonical fields exist.
- Frontend should handle mode-driven behavior via room_mode endpoints.

## 4.4 Bot runtime depth

Current weak agent is implemented with heuristic decision-making (ported from legacy weakAgent flow). Further improvements are still possible:

- add bot lifecycle tests (join, act, complete round)

## 5. Frontend Adaptation Guide

Use this migration order for minimum breakage.

1. Command routing:
   - Replace direct calls to virtual/physical APIs with /game/command/... and /game/query/... on gateway.
2. Mode control:
   - set room mode with POST /game/room_mode/{game_id}.
3. State/events:
   - read canonical state from /game/state/canonical and consume /game/event stream payloads from gateway.
4. Camera path:
   - use gateway WebSocket /ws/camera/{game_id}; do not connect frontend directly to CV service.
5. Error handling:
   - unify against gateway response shape {success, message, ...}.

## 6. Suggested Next Milestones

1. HTTPS baseline:
   - add reverse-proxy TLS and secure headers
   - add auth token/session middleware in gateway
2. Broker baseline:
   - introduce shared/messaging interfaces and first topic set
   - publish room state/events from both engines through broker adapters
3. Frontend cutover:
   - remove all direct engine URLs from frontend configuration
   - validate only gateway-facing integration
4. MVP hardening tests:
   - add full virtual room flow tests
   - add physical CV->game mocked integration tests
   - add broker and auth smoke tests
