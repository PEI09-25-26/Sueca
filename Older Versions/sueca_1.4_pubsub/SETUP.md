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

---

## Cloudflare Tunnel - Rodar noutro PC

### 1. Instalar cloudflared

```bash
# Linux/macOS
curl -L --output cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.tgz
tar -xzf cloudflared.tgz
sudo mv cloudflared /usr/local/bin/

# Windows (PowerShell Admin)
choco install cloudflare-warp
# Ou descarregar de: https://github.com/cloudflare/cloudflared/releases
```

### 2. Terminal 2 - Rodar o túnel Cloudflare

```bash
cd /caminho/para/Sueca/sueca_1.4_pubsub

cloudflared tunnel --config apps/cloudflare/config.yml run sueca-api
```

### 3. Verificar que está a funcionar

```bash
# De qualquer PC (até fora da rede):
curl -s https://api.suecadaojogo.com/system/services | jq
```
