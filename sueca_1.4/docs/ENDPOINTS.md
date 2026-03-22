# Sueca 1.4 Endpoint Catalog

This file documents all known HTTP and WebSocket endpoints in the current architecture.

## Base URLs

- Gateway (external entrypoint): http://localhost:8000
- Virtual engine service (internal): http://localhost:5000
- Physical game service (internal): http://localhost:8002
- Physical CV service (internal HTTP): http://localhost:8001
- Physical CV service (internal WebSocket): ws://localhost:8001

## External Endpoints (Gateway)

These are the endpoints that clients should call first.

### Gateway HTTP

#### POST /game/state
- Receives:
  - body: raw room/game state object from virtual engine
- Returns:
  - `{ ok, contract: "sueca.room_state.v1", canonical }`

#### POST /game/physical/state
- Receives:
  - body: raw room/game state object from physical engine
- Returns:
  - `{ ok, contract: "sueca.room_state.v1", canonical }`

#### POST /game/event
- Receives:
  - body: raw event object from virtual engine
- Returns:
  - `{ ok, contract: "sueca.event.v1", event_type }`

#### POST /game/physical/event
- Receives:
  - body: raw event object from physical engine
- Returns:
  - `{ ok, contract: "sueca.event.v1", event_type }`

#### GET /game/state
- Receives: no arguments
- Returns:
  - latest raw state object received by gateway

#### GET /game/state/canonical
- Receives: no arguments
- Returns:
  - latest normalized canonical room state

#### GET /game/state/canonical/{game_id}
- Receives:
  - path: `game_id`
- Returns:
  - canonical room state for that game, or `{}` if unknown

#### POST /game/room_mode/{game_id}
- Receives:
  - path: `game_id`
  - body: `{ mode }` where mode is `virtual` or `physical` (other values normalize to virtual)
- Returns:
  - `{ success, game_id, mode }`

#### GET /game/room_mode/{game_id}
- Receives:
  - path: `game_id`
- Returns:
  - `{ success, game_id, mode }` (defaults to `virtual`)

#### POST /game/command/{command:path}
- Receives:
  - path: `command` dynamic sub-path (supports nested paths)
  - body: `{ game_id?, mode?, payload }`
  - behavior: resolves target by mode and forwards payload to selected engine
- Returns:
  - success: `{ success, mode, target, response }`
  - error: `{ success: false, mode, target, message }`

#### GET /game/query/{query_path:path}
- Receives:
  - path: `query_path` dynamic sub-path
  - query: `game_id?`, `mode?`
  - behavior: resolves target by mode and forwards GET query
- Returns:
  - success: `{ success, mode, target, response }`
  - error: `{ success: false, mode, target, message }`

#### GET /system/services
- Receives: no arguments
- Returns:
  - `{ autostart, services }` where each service includes `{ url, healthy, managed }`

#### POST /game/round_end
- Receives:
  - body: `{ round_number, winner_team, winner_points, team1_points, team2_points, game_ended }`
- Returns:
  - `{ success: true }`

#### POST /game/new_round/{game_id}
- Receives:
  - path: `game_id`
- Returns:
  - success: `{ success: true, message }`
  - error: `{ success: false, message }`

#### POST /game/start
- Receives:
  - body: `{ playerName, roomId? }`
- Returns:
  - `{ success, message, gameId }`

#### POST /game/ready/{game_id}
- Receives:
  - path: `game_id`
- Returns:
  - success: `{ success: true, message }`
  - error: `{ success: false, message }`

#### POST /scan
- Receives:
  - body: `{ source, success, message, detection? }`
  - detection shape: `{ rank, suit, confidence }`
- Returns:
  - success: `{ success: true, message, backend_response, detection }`
  - error: `{ success: false, message, detection? }`

### Gateway WebSocket

#### WS /ws/camera/{game_id}
- Receives:
  - path: `game_id`
  - inbound messages: camera frame text payload (base64 image)
- Returns / pushes:
  - JSON messages containing CV detections and game updates, typically:
    - `{ success: true, detection, game_state }`
    - or passthrough CV payloads/errors

## Internal Endpoints

These are service endpoints that are normally called by the gateway or service-to-service flows.

### Virtual Engine (apps/virtual_engine)

Base URL: http://localhost:5000

#### GET /api/status
- Receives:
  - query: `game_id?`
- Returns:
  - full game state object
  - 404 error JSON when game is not found

#### GET /api/room/{game_id}/lobby
- Receives:
  - path: `game_id`
- Returns:
  - `{ success, game_id, phase, player_count, max_players, available_slots, teams }`

#### GET /api/room/{game_id}/history
- Receives:
  - path: `game_id`
- Returns:
  - `{ success, game_id, matches_played, history }`

#### GET /api/room/{game_id}/match_points
- Receives:
  - path: `game_id`
- Returns:
  - `{ success, game_id, points, teams, matches_played }`

#### POST /api/room/{game_id}/rematch
- Receives:
  - path: `game_id`
- Returns:
  - success: `{ success: true, message, state }`
  - error: `{ success: false, message }`

#### POST /api/create_room
- Receives: no arguments
- Returns:
  - `{ success: true, game_id }`

#### POST /api/create_game
- Receives:
  - body: `{ name, position? }`
- Returns:
  - `{ success, message, game_id, player_id }`

#### POST /api/join
- Receives:
  - body: `{ game_id?, name, position? }`
- Returns:
  - `{ success, message, game_id, player_id }`

#### POST /api/change_position
- Receives:
  - body: `{ game_id?, player_id|player, position }`
- Returns:
  - success: `{ success: true, message, state }`
  - validation/error: `{ success: false, message }`

#### POST /api/add_bot
- Receives:
  - body: `{ game_id?, player_id, position, name?, difficulty? }`
  - supported `difficulty` values: `random`, `weak`, `weak_agent`
- Returns:
  - success with bot id when available: `{ success, message, game_id, player_id }`
  - success while joining: `{ success, message, game_id, player_id: null }`
  - error JSON on authorization/validation failures

#### POST /api/start
- Receives:
  - body: `{ game_id? }`
- Returns:
  - `{ success, message }`

#### POST /api/cut_deck
- Receives:
  - body: `{ game_id?, player_id|player, index }`
- Returns:
  - `{ success, message }`

#### POST /api/select_trump
- Receives:
  - body: `{ game_id?, player_id|player, choice }`
- Returns:
  - `{ success, message }`

#### GET /api/hand/{player_id}
- Receives:
  - path: `player_id`
  - query: `game_id?`
- Returns:
  - success: `{ success: true, hand }`
  - error: `{ success: false, message }`

#### POST /api/play
- Receives:
  - body: `{ game_id?, player_id|player, card }`
- Returns:
  - `{ success, message }`

#### POST /api/remove_player
#### POST /api/the_council_has_decided_your_fate
- Receives:
  - body: `{ game_id?, actor_id, target_id }`
- Returns:
  - `{ success, message }`

#### POST /api/reset
- Receives:
  - body: `{ game_id? }`
- Returns:
  - `{ success: true, message: "Game reset" }` or not-found error

### Physical Game Service (apps/physical_engine)

Base URL: http://localhost:8002

#### GET /state
- Receives: no arguments
- Returns:
  - current referee/game state object

#### POST /reset
- Receives: no arguments
- Returns:
  - `{ success: true, message: "Game reset" }`

#### POST /new_round
- Receives: no arguments
- Returns:
  - `{ success: true, message, round }`

#### POST /card
- Receives:
  - body: `{ rank, suit, confidence? }`
- Returns:
  - on normal queue: `{ success: true, message: "Card queued", current_player, queue_size }`
  - when trump is set: `{ success: true, message: "Trump card set" }`
  - invalid card: `{ success: false, message: "Invalid card" }`

### Physical CV Service (apps/physical_engine)

Base URL: http://localhost:8001

#### POST /cv/start
- Receives:
  - body: `{ game_id }`
- Returns:
  - `{ success, message, has_classifier }`

#### POST /cv/stop
- Receives:
  - query: `game_id`
- Returns:
  - `{ success: true, message: "CV service stopped" }` or `{ success: false, message: "Game not found" }`

#### GET /health
- Receives: no arguments
- Returns:
  - `{ status, detector_loaded, classifier_loaded, active_games }`

#### WS /cv/stream/{game_id}
- Receives:
  - path: `game_id`
  - inbound text messages:
    - base64 frame strings
    - optional command JSON such as `{ "action": "reset_cards" }`
- Returns / pushes:
  - detections in JSON: `{ success: true, detection: { rank, suit, confidence, position } }`
  - command ack: `{ success: true, message: "cards_reset" }`
  - init error payload when CV service is not started

## Proxy Behavior (Gateway -> Internal)

The gateway can route by mode using room mode mapping or explicit mode in payload.

### Command Proxy

- Entry: POST /game/command/{command:path}
- Virtual mode target: POST http://localhost:5000/api/{command}
- Physical mode target: POST http://localhost:8002/{command}

Examples:

- POST /game/command/create_game -> virtual /api/create_game
- POST /game/command/room/{game_id}/rematch -> virtual /api/room/{game_id}/rematch
- POST /game/command/card -> physical /card

### Query Proxy

- Entry: GET /game/query/{query_path:path}?game_id=...&mode=...
- Virtual mode target: GET http://localhost:5000/api/{query_path}
- Physical mode target: GET http://localhost:8002/{query_path}

Examples:

- GET /game/query/status -> virtual /api/status
- GET /game/query/hand/{player_id}?game_id=... -> virtual /api/hand/{player_id}
- GET /game/query/state -> physical /state

## Integration Notes

- Canonical room state and event ingestion is done through:
  - POST /game/state and POST /game/physical/state
  - POST /game/event and POST /game/physical/event
- Mobile camera flow uses:
  - client -> gateway WS /ws/camera/{game_id}
  - gateway -> CV WS /cv/stream/{game_id}
  - gateway -> game service POST /card
- Service health checks used by gateway autostart:
  - virtual: GET /api/status
  - physical CV: GET /health
  - physical game: GET /state

## Common Error Shape

Several endpoints (especially virtual engine) return this standard error object:

- `{ success: false, message: "..." }`
