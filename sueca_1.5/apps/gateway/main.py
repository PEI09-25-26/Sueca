import asyncio
import json

from fastapi import FastAPI
import requests

from .lifecycle import shutdown_services, startup_services
from .routes import game_router, proxy_router, state_router, websocket_router
from . import state
from apps.emqx.mqtt_client import connect_mqtt, disconnect_mqtt, client as mqtt_client

app = FastAPI(title="CV Middleware", version="0.1")

def on_mqtt_message(client, userdata, msg):
    try:
        topic = msg.topic
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
        mqtt_client.on_message = on_mqtt_message
        print("[Middleware] Subscribed to MQTT hybrid and state topics")
    startup_services()

@app.on_event("shutdown")
def shutdown():
    shutdown_services()
    disconnect_mqtt()

app.include_router(state_router)
app.include_router(proxy_router)
app.include_router(game_router)
app.include_router(websocket_router)
