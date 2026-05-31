import asyncio
import datetime
import json
import uuid

import jwt
from fastapi import FastAPI
import requests

from .lifecycle import shutdown_services, startup_services
from .routes import game_router, proxy_router, state_router, websocket_router
from . import state
from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt, client as mqtt_client

app = FastAPI(title="CV Middleware", version="0.1")

def on_mqtt_message(client, userdata, msg):
    print(f"[Middleware] MQTT message received on topic: {msg.topic}")
    try:
        topic = msg.topic
        if topic.startswith("sueca/presence/"):
            parts = topic.split("/")
            if len(parts) == 3:
                uid = parts[2]
                status = msg.payload.decode().strip()
                print(f"[Middleware] PRESENCE UPDATE: user={uid}, status={status}")
                if status in ["online", "offline"]:
                    async def update_status():
                        try:
                            headers = {}
                            if state.SUECA_SERVICE_JWT_SECRET:
                                # Issue a short-lived service token locally to call the auth service
                                now = datetime.datetime.now(datetime.timezone.utc)
                                payload = {
                                    "service": "gateway",
                                    "scope": "control_plane",
                                    "iat": now,
                                    "exp": now + datetime.timedelta(minutes=5),
                                    "jti": str(uuid.uuid4()),
                                    "type": "service",
                                }
                                token = jwt.encode(payload, state.SUECA_SERVICE_JWT_SECRET, algorithm="HS256")
                                headers["Authorization"] = f"Bearer {token}"
                                print(f"[Middleware] Generated service token for presence update (uid={uid})")

                            print(f"[Middleware] Calling Auth Service internal status update for {uid} -> {status}")
                            resp = await asyncio.to_thread(
                                state.INTERNAL_HTTP.put,
                                f"{state.AUTH_SERVICE_URL}/user/{uid}/status",
                                json={"uid": uid, "status": status},
                                headers=headers,
                                timeout=2
                            )
                            if resp.status_code == 200:
                                print(f"[Middleware] Successfully updated presence for {uid} to {status}")
                            else:
                                print(f"[Middleware] Failed to update status for {uid}: HTTP {resp.status_code} - {resp.text}")
                        except Exception as e:
                            print(f"[Middleware] Error updating status for {uid}: {e}")
                    
                    loop = state.main_loop
                    if loop and not loop.is_closed():
                        asyncio.run_coroutine_threadsafe(update_status(), loop)
                else:
                    print(f"[Middleware] Ignoring invalid status value: {status}")
            return

        if not topic.startswith("sueca/games/") or (not topic.endswith("/hybrid") and not topic.endswith("/state")):
            return
            
        parts = topic.split("/")
        if len(parts) != 4:
            return
            
        game_id = parts[2]
        
        if game_id not in state.hybrid_stream_connections:
            return
            
        payload = json.loads(msg.payload.decode())

        if topic.endswith("/state"):
            broadcast_payload = {
                "type": "state_update",
                "game_state": payload.get("state", payload),
            }
        elif topic.endswith("/hybrid"):
            broadcast_payload = {
                "type": "state_update",
                "hybrid_state": payload.get("hybrid_state", payload),
            }
        else:
            return
        
        async def broadcast():
            for ws in state.hybrid_stream_connections.get(game_id, []):
                try:
                    await ws.send_text(json.dumps(broadcast_payload))
                except Exception:
                    pass
                    
        loop = state.main_loop
        if loop and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(broadcast(), loop)
    except Exception as e:
        print(f"[Middleware] MQTT bridge error: {e}")

@app.on_event("startup")
async def startup():
    state.main_loop = asyncio.get_running_loop()
    if connect_mqtt():
        mqtt_client.subscribe("sueca/games/+/hybrid", qos=1)
        mqtt_client.subscribe("sueca/games/+/state", qos=1)
        mqtt_client.subscribe("sueca/presence/+", qos=1)
        mqtt_client.on_message = on_mqtt_message
        print("[Middleware] Subscribed to MQTT hybrid, state and presence topics")
    startup_services()

@app.on_event("shutdown")
def shutdown():
    shutdown_services()
    disconnect_mqtt()

app.include_router(state_router)
app.include_router(proxy_router)
app.include_router(game_router)
app.include_router(websocket_router)
