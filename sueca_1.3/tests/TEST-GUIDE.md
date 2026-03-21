## Sueca API Test Guide (Single-Line Commands)

Use this guide exactly in order. Every command is a single line so you can copy/paste directly.

### 1. Open project folder

    cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3"

### 2. Activate venv

    source venv/bin/activate

### 3. Install dependencies

    python -m pip install -r requirements.txt

### 4. Start Flask server (Terminal A)

    python server.py

Leave Terminal A running.

### 5. Start middleware (Terminal B)

    cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3" && source venv/bin/activate && uvicorn middleware:app --reload --host 0.0.0.0 --port 8000

Leave Terminal B running.

### 6. Health checks (Terminal C)

    cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3" && source venv/bin/activate && curl -s http://127.0.0.1:5000/api/status

    cd "/home/daniel-andrade-martins/Desktop/Engenharia Informática/3º Ano/2º Semestre/Projeto em Engenharia Informática/Sueca/sueca_1.3" && source venv/bin/activate && curl -s http://127.0.0.1:8000/game/status

### 7. Create a game and host player

    curl -s -X POST http://127.0.0.1:5000/api/create_game -H "Content-Type: application/json" -d '{"name":"Host","position":"NORTH"}'

Save these values from the response:
- game_id
- player_id (this is the host id, used as actor_id)

### 8. Join second player

Replace YOUR_GAME_ID with the game_id from step 7.

    curl -s -X POST http://127.0.0.1:8000/game/join -H "Content-Type: application/json" -d '{"name":"Guest","position":"EAST","game_id":"YOUR_GAME_ID"}'

Save player_id from this response (this is target_id).

### 9. Remove second player with council endpoint

Replace values with your real ids.

    curl -s -X POST http://127.0.0.1:8000/game/the_council_has_decided_your_fate -H "Content-Type: application/json" -d '{"actor_id":"YOUR_HOST_PLAYER_ID","target_id":"YOUR_GUEST_PLAYER_ID","game_id":"YOUR_GAME_ID"}'

### 10. Verify result

    curl -s "http://127.0.0.1:5000/api/status?game_id=YOUR_GAME_ID"

If successful, the removed player should no longer appear in the room state.

### Common mistakes

- Error 415 Unsupported Media Type: you forgot -H "Content-Type: application/json".
- -H: command not found: your curl command was split across lines without proper continuation.
- Actor player not found: actor_id is wrong, or does not belong to this game.
- Only the host can remove players: actor_id must be the first player that created/joined the game.