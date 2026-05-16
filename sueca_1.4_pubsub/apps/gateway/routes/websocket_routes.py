import asyncio
import json

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import state
from apps.virtual_engine.session import session_manager


router = APIRouter()


def _extract_ws_token(websocket: WebSocket) -> str | None:
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    try:
        return websocket.query_params.get("token")
    except Exception:
        return None


@router.websocket("/ws/camera/{game_id}")
async def websocket_camera(websocket: WebSocket, game_id: str):
    token = _extract_ws_token(websocket)

    if not token:
        await websocket.close(code=4001)
        print(f"[Middleware] Missing token for game {game_id}")
        return
    # Validate the token using the session manager to ensure it is an active room session
    payload = session_manager.validate_token(token)
    if not payload:
        await websocket.close(code=4002)
        print(f"[Middleware] Token validation failed for {game_id}")
        return

    if payload.get("game_id") != game_id:
        await websocket.close(code=4003)
        print(f"[Middleware] Token game_id mismatch for {game_id}")
        return

    await websocket.accept()
    state.active_connections[game_id] = websocket
    print(f"[Middleware] Mobile WebSocket connected for game: {game_id}")

    cv_ws = None
    try:
        cv_ws = await websockets.connect(
            f"{state.CV_SERVICE_WS_URL}/cv/stream/{game_id}",
            additional_headers={"Authorization": f"Bearer {token}"},
        )
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
                                    "game_id": game_id,
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
                                # Log backend error but avoid echoing internal backend text to clients
                                print(f"[Middleware] Game Service HTTP {game_response.status_code}")
                                await websocket.send_json({"success": False, "detection": detection, "message": "game service unavailable"})
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
