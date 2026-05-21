import asyncio
import json

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import state


router = APIRouter()


@router.websocket("/ws/camera/{game_id}")
async def websocket_camera(websocket: WebSocket, game_id: str):
    await websocket.accept()
    state.active_connections[game_id] = websocket
    print(f"[Middleware] Mobile WebSocket connected for game: {game_id}")

    cv_ws = None
    try:
        cv_ws = await websockets.connect(f"{state.CV_SERVICE_WS_URL}/cv/stream/{game_id}")
        state.cv_connections[game_id] = cv_ws
        print(f"[Middleware] Connected to CV Service WebSocket for game: {game_id}")

        async def receive_from_cv():
            try:
                async for message in cv_ws:
                    data = json.loads(message)
                    if data.get("success") and data.get("detection"):
                        detection = data["detection"]
                        print(f"[Middleware] Received detection from CV: {detection}")

                        try:
                            suit_symbol = state.SUIT_SYMBOLS.get(detection["suit"], detection["suit"])

                            game_response = await asyncio.to_thread(
                                state.INTERNAL_HTTP.post,
                                f"{state.GAME_SERVICE_URL}/card",
                                json={
                                    "rank": detection["rank"],
                                    "suit": suit_symbol,
                                    "confidence": detection.get("confidence", 1.0),
                                },
                                timeout=2,
                            )
                            if game_response.status_code == 200:
                                game_result = game_response.json()
                                print(f"[Middleware] Game Service response: {game_result}")

                                combined_data = {
                                    "success": True,
                                    "detection": detection,
                                    "game_state": game_result,
                                }
                                await websocket.send_json(combined_data)
                            else:
                                print(
                                    f"[Middleware] Game Service HTTP {game_response.status_code}: {game_response.text}"
                                )
                                await websocket.send_json(data)
                        except Exception as error:
                            print(f"[Middleware] Error sending to Game Service: {error}")
                            await websocket.send_json(data)
            except Exception as error:
                print(f"[Middleware] Error receiving from CV: {error}")

        asyncio.create_task(receive_from_cv())

        while True:
            frame_data = await websocket.receive_text()
            await cv_ws.send(frame_data)
    except WebSocketDisconnect:
        print(f"[Middleware] Mobile WebSocket disconnected for game: {game_id}")
    except Exception as error:
        print(f"[Middleware] WebSocket error: {error}")
    finally:
        if game_id in state.active_connections:
            del state.active_connections[game_id]
        if cv_ws:
            await cv_ws.close()
        if game_id in state.cv_connections:
            del state.cv_connections[game_id]
        print(f"[Middleware] Cleaned up connections for game: {game_id}")
