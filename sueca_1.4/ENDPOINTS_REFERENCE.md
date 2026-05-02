# Sueca 1.4 Endpoints Reference

## Service Base URLs

- Gateway: http://localhost:8080
- Virtual Engine: http://localhost:5000
- Physical CV: http://localhost:8001
- Physical Game: http://localhost:8002

## Gateway Endpoints

### Room mode and routing

- POST /game/room_mode/{game_id}
  - Body: { mode }
  - Purpose: set room mode to virtual or physical
- GET /game/room_mode/{game_id}
  - Purpose: get current room mode
- POST /game/command/{command_path}
  - Body: { game_id?, mode?, payload }
  - Purpose: forward command to selected engine
- GET /game/query/{query_path}
  - Query: game_id?, mode?
  - Purpose: forward read/query request to selected engine

### State and event aggregation

- POST /game/state
- GET /game/state
- GET /game/state/canonical
- GET /game/state/canonical/{game_id}
- POST /game/event
- POST /game/physical/state
- POST /game/physical/event

### Gateway utility

- GET /system/services
  - Purpose: check managed service health
- POST /game/start
- POST /game/ready/{game_id}
- POST /game/new_round/{game_id}
- POST /game/round_end
- POST /scan
- WS /ws/camera/{game_id}

## Virtual Engine Endpoints

### Room and lobby

- GET /api/status?game_id=
- GET /api/room/{game_id}/lobby
- GET /api/room/{game_id}/history
- GET /api/room/{game_id}/match_points
- POST /api/create_room
- POST /api/create_game
  - Body: { name, position }
- POST /api/join
  - Body: { game_id, name, position }
- POST /api/room/{game_id}/rematch

### Player and bots

- POST /api/change_position
  - Body: { game_id?, player_id|player, position }
- POST /api/add_bot
  - Body: { game_id?, player_id, position, name?, difficulty? }
  - difficulty values: random, weak, weak_agent
- POST /api/remove_player
- POST /api/the_council_has_decided_your_fate
  - Body: { game_id?, actor_id, target_id }

### Gameplay

- POST /api/start
- POST /api/cut_deck
  - Body: { game_id?, player_id|player, index }
- POST /api/select_trump
  - Body: { game_id?, player_id|player, choice }
- GET /api/hand/{player_id}?game_id=
- POST /api/play
  - Body: { game_id?, player_id|player, card }
- POST /api/reset

## Physical CV Endpoints

- POST /cv/start
  - Body: { game_id }
- POST /cv/stop?game_id=
- GET /health
- WS /cv/stream/{game_id}

## Physical Game Endpoints

- GET /state
- POST /reset
- POST /new_round
- POST /card
  - Body: { rank, suit, confidence? }
