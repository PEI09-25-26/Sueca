# Virtual Engine

Virtual game runtime for Sueca 1.4.

## Structure

- api.py: FastAPI entrypoint.
- core/game_core.py: match state, rules, and room manager.
- routes/: API routes split by concern.
  - room_routes.py
  - player_routes.py
  - gameplay_routes.py
- agents/: playable bot agents.
  - random_agent/
  - weak_agent/
- clients/: CLI client integration layer.
- server.py: compatibility re-export of api.app.

## Bot Types

Available in POST /api/add_bot via difficulty:

- random
- weak
- weak_agent
