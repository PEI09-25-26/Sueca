# Sueca 1.4 Architecture and Migration Plan

This document tracks the migration from legacy Sueca layouts into the current service-oriented Sueca 1.4 structure and the remaining roadmap items.

## Current Architecture (Implemented)

## Domains

- apps/gateway
- apps/virtual_engine
- apps/physical_engine
- shared/contracts
- shared/config
- docs

## Gateway

- Entry: apps/gateway/main.py
- Route modules:
  - apps/gateway/routes/state_routes.py
  - apps/gateway/routes/proxy_routes.py
  - apps/gateway/routes/game_routes.py
  - apps/gateway/routes/websocket_routes.py
- Orchestration lifecycle:
  - apps/gateway/lifecycle.py
- Shared gateway internals:
  - apps/gateway/helpers.py
  - apps/gateway/state.py
  - apps/gateway/dto.py

Responsibilities:

- Canonical integration entrypoint for clients
- mode-aware routing (virtual vs physical)
- service status and local autostart in dev mode
- canonical state/event ingestion

## Virtual Engine

- Entry: apps/virtual_engine/api.py
- Core: apps/virtual_engine/core/game_core.py
- Route package:
  - apps/virtual_engine/routes/room_routes.py
  - apps/virtual_engine/routes/player_routes.py
  - apps/virtual_engine/routes/gameplay_routes.py
- Bot agents:
  - apps/virtual_engine/agents/random_agent
  - apps/virtual_engine/agents/weak_agent

Responsibilities:

- room lifecycle and multiplayer game state
- deck cut, trump selection, rounds and scoring
- add_bot flow through bot factory

## Physical Engine

- Service entries:
  - apps/physical_engine/game_service.py
  - apps/physical_engine/cv_service.py
- Route package:
  - apps/physical_engine/routes/game_routes.py
  - apps/physical_engine/routes/cv_routes.py
- Core:
  - apps/physical_engine/core/game_core.py
  - apps/physical_engine/core/cv_core.py

Responsibilities:

- physical-card referee/game state
- CV stream ingestion and card detection/classification

## Shared Contracts

- shared/contracts/models.py
- shared/contracts/normalizers.py

Responsibilities:

- canonical room/event envelope
- normalization across virtual and physical runtimes

## What Was Migrated

- Legacy middleware-centric flow consolidated into apps/gateway.
- Legacy virtual Flask layout refactored into FastAPI + modular routes.
- Legacy physical runtime reorganized into apps/physical_engine with separated services.
- Canonical contracts introduced and wired into gateway state/event ingestion.

## Remaining Migration and Hardening Roadmap

## Phase A: Frontend Cutover Completion

- Ensure frontend calls only gateway endpoints.
- Remove direct virtual/physical endpoint usage from frontend code.
- Standardize frontend handling on canonical state/event payloads.

## Phase B: Security Baseline

- Add session concept (room + player binding).
- Add token issuance/validation.
- Add command authorization checks and turn-ownership guards.

## Phase C: HTTPS Rollout

- Introduce TLS termination (proxy or ingress).
- Enforce secure transport and security headers.

## Phase D: Message Broker Rollout

- Add shared messaging abstractions (topics, publisher, subscriber).
- Publish state/events through broker adapters.
- Reduce polling in favor of event streams where feasible.

## Validation Baseline

- Automation suite runner: run_automation_tests.py
- Latest baseline in this branch: tests passing after gateway/virtual modularization and weak-agent integration.
