# Hybrid Engine Documentation

## Overview

The Hybrid Engine is an **independent Docker service** that combines:
- **Virtual Engine game logic** (game state, AI agents)
- **Built-in CV integration** (card recognition via YOLO)

Unlike the traditional setup where Virtual and Physical engines run separately, the Hybrid Engine is a **unified service** running on port 8002 that handles both game logic AND computer vision in a single container.

## Architecture

```
Frontend (Android)
    ↓ HTTP/WS (Bearer token)
    ↓
Gateway (Port 8080)
    ↓ Routes based on mode:
    ├─ mode=virtual   → Virtual Engine (5000)
    ├─ mode=physical  → Physical Engine (8001)
    └─ mode=hybrid    → Hybrid Engine (8002) ★ NEW
    ↓
Hybrid Engine (Port 8002)
    ├─ Game Logic (from Virtual Engine)
    ├─ Built-in CV (from Physical Engine)
    └─ Pub/Sub to MQTT
```

## Starting the Hybrid Engine

### Option 1: Full Stack (all services)
```bash
cd /home/pedro/Documentos/PEI/Sueca/sueca_1.5
docker-compose up -d
```

This starts:
- Gateway (8080)
- Virtual Engine (5000)
- Physical Engine (8001)
- **Hybrid Engine (8002)** ← New
- Auth (5010)
- MQTT (1883)
- etc.

### Option 2: Hybrid Mode Only
```bash
docker-compose up -d hybrid_engine auth emqx
```

This starts only:
- Hybrid Engine (8002)
- Auth (5010)
- MQTT (1883)

Then configure frontend to use hybrid mode.

### Option 3: Hybrid + Gateway (Recommended Hybrid Setup)
```bash
docker-compose up -d hybrid_engine gateway auth emqx agents
```

This allows frontend to route through Gateway with mode=hybrid.

## Configuration

### Environment Variables

The Hybrid Engine uses standard `.env` file configuration:

```bash
# .env
HYBRID_ENGINE_URL=http://hybrid_engine:8002
MQTT_SERVICE=hybrid_engine
SUECA_YOLO_DEVICE=cpu  # or gpu
```

**Key differences from Virtual Engine**:
- Includes CV dependencies (opencv-python-headless)
- YOLO model loaded on startup
- Can handle both virtual and real card detection

## API Routes

### Same as Virtual Engine

**Note**: Hybrid Engine exposes the same REST API as Virtual Engine:

- `POST /api/create_room` - Create room
- `POST /api/start` - Start game
- `POST /api/play` - Play card
- `POST /api/join` - Join game
- `GET /api/status` - Get state
- etc.

### Plus Hybrid-Specific Routes (via Gateway)

When called through Gateway with `?mode=hybrid`:

- `POST /game/command/create_room?mode=hybrid` → Routes to Hybrid Engine
- `POST /api/hybrid/register_player` - Register as real/virtual
- `POST /api/hybrid/confirm_play` - Host confirms virtual play
- `WS /cv/stream/{game_id}` - CV WebSocket stream (built-in)

## Workflow Example

### 1. Create a Hybrid Game

```bash
curl -X POST http://localhost:8080/game/command/create_room \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "Pedro"}' \
  -G -d "mode=hybrid"
```

Response:
```json
{
  "success": true,
  "http_status": 200,
  "mode": "hybrid",
  "target": "http://hybrid_engine:8002/api/create_room",
  "response": {
    "success": true,
    "game_id": "12345"
  }
}
```

### 2. Register Players (Real + Virtual)

```bash
# Register real player (host)
curl -X POST http://hybrid_engine:8002/api/hybrid/register_player \
  -H "Authorization: Bearer <token>" \
  -d '{
    "game_id": "12345",
    "player_id": "real_player_1",
    "role": "real",
    "is_host": true
  }'

# Register AI player (virtual)
curl -X POST http://hybrid_engine:8002/api/hybrid/register_player \
  -H "Authorization: Bearer <token>" \
  -d '{
    "game_id": "12345",
    "player_id": "ai_1",
    "role": "virtual",
    "is_host": false
  }'
```

### 3. Start Game & Deal Cards

```bash
curl -X POST http://hybrid_engine:8002/api/hybrid/deal_cards \
  -H "Authorization: Bearer <token>" \
  -d '{
    "game_id": "12345",
    "host_player_id": "real_player_1",
    "virtual_player_ids": ["ai_1"],
    "cards_per_virtual": 10
  }'
```

### 4. Deal Cards via CV

Real player uses camera to show cards:

```bash
# WebSocket stream on hybrid_engine
ws://hybrid_engine:8002/cv/stream/12345

# Send frame
{"action": "reset_cards"}
<base64_encoded_frame>

# Receive detection
{"detection": {"rank": "K", "suit": "Hearts", "card_id": 12}}
```

### 5. Distribute to Virtual Players

```bash
curl -X POST http://hybrid_engine:8002/api/hybrid/deal_cards \
  -d '{"game_id": "12345", "player_id": "ai_1", "card_id": 12}'
```

## Docker Build

The Hybrid Engine Dockerfile is at: `apps/hybrid_engine/Dockerfile`

**Build individually**:
```bash
docker build -f apps/hybrid_engine/Dockerfile -t sueca-hybrid-engine:latest .
```

**Rebuild in docker-compose**:
```bash
docker-compose build hybrid_engine
docker-compose up -d hybrid_engine
```

## Logs

View hybrid engine logs:

```bash
docker logs sueca_1.5-hybrid_engine-1 -f
```

Or use docker-compose:

```bash
docker-compose logs -f hybrid_engine
```

## Troubleshooting

### "Connection refused" to Hybrid Engine

1. Check if service is running:
   ```bash
   docker ps | grep hybrid_engine
   ```

2. Check logs:
   ```bash
   docker-compose logs hybrid_engine
   ```

3. Verify port 8002 is exposed:
   ```bash
   docker-compose ps
   ```

### CV Service not loading

The Hybrid Engine includes YOLO model loading on startup. If it hangs:

1. Check YOLO download:
   ```bash
   docker exec sueca_1.5-hybrid_engine-1 ls /app/apps/physical_engine/cv
   ```

2. Download model manually:
   ```bash
   docker exec sueca_1.5-hybrid_engine-1 \
     python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
   ```

### MQTT Connection Issues

Verify MQTT is running:
```bash
docker-compose logs emqx | grep "EMQX"
```

Hybrid Engine should connect automatically via `paho-mqtt` library.

## Performance Notes

- **CPU-based YOLO**: Slower but works everywhere (set `SUECA_YOLO_DEVICE=cpu`)
- **GPU-based YOLO**: Faster, requires NVIDIA GPU (set `SUECA_YOLO_DEVICE=cuda`)

## Next Steps

1. **Test Hybrid Mode**:
   ```bash
   docker-compose up -d
   # Then use frontend with mode=hybrid
   ```

2. **Fine-tune CV**:
   - Adjust YOLO model (yolo11n.pt, yolo11s.pt, etc.)
   - Calibrate camera settings

3. **Monitor Performance**:
   - Check latency between CV detection and game state
   - Optimize AI decision-making for real-time play

## Files

- **Dockerfile**: `apps/hybrid_engine/Dockerfile`
- **Requirements**: `apps/hybrid_engine/requirements.txt`
- **Entry Point**: `apps/hybrid_engine/main.py`
- **Docker Compose**: `docker-compose.yml` (service: `hybrid_engine`)
- **Config**: `shared/config/services.py` (HYBRID_ENGINE_URL)
- **Gateway Routing**: `apps/gateway/helpers.py` (target_base_for_mode)
