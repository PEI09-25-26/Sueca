# Sueca 1.4 Pub/Sub Setup

From workspace root:

```bash
export MQTT_BROKER_HOST=127.0.0.1
export MQTT_BROKER_PORT=1883
export PYTHONPATH="$PWD"
python3 -m uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8080
```

## 4. Verify Backend Health

In another terminal:

```bash
curl -s http://127.0.0.1:8080/system/services | jq
```

Expected:
- `virtual_engine.healthy = true`
- `physical_cv.healthy = true`
- `physical_game.healthy = true`