import asyncio
import json
import logging

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import state
from apps.virtual_engine.session import session_manager


router = APIRouter()

logger = logging.getLogger("gateway.websocket")


def _extract_ws_token(websocket: WebSocket) -> str | None:
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    # Do not accept tokens in query parameters for security reasons.
    return None


@router.websocket("/ws/camera/{game_id}")
async def websocket_camera(websocket: WebSocket, game_id: str):
    token = _extract_ws_token(websocket)

    if not token:
        await websocket.close(code=4001)
        logger.warning("Missing token for game %s", game_id)
        return
    # Validate the token using the session manager to ensure it is an active room session
    payload = session_manager.validate_token(token)
    if not payload:
        await websocket.close(code=4002)
        logger.warning("Token validation failed for %s", game_id)
        return

    if payload.get("game_id") != game_id:
        await websocket.close(code=4003)
        logger.warning("Token game_id mismatch for %s", game_id)
        return

    await websocket.accept()
    state.active_connections[game_id] = websocket
    logger.info("Mobile WebSocket connected for game: %s", game_id)

    cv_ws = None
    try:
        cv_ws = await websockets.connect(
            f"{state.CV_SERVICE_WS_URL}/cv/stream/{game_id}",
            additional_headers={"Authorization": f"Bearer {token}"},
        )
        state.cv_connections[game_id] = cv_ws
        logger.info("Connected to CV Service WebSocket for game: %s", game_id)

        async def receive_from_cv():
            try:
                async for message in cv_ws:
                    data = json.loads(message)
                    if data.get("success") and data.get("detection"):
                        detection = data["detection"]
                        logger.debug("Received detection from CV: %s", detection)

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
                                logger.debug("Game Service response: %s", game_result)

                                combined_data = {
                                    "success": True,
                                    "detection": detection,
                                    "game_state": game_result,
                                }
                                await websocket.send_json(combined_data)
                            else:
                                # Log backend error but avoid echoing internal backend text to clients
                                logger.warning("Game Service HTTP %s for game %s", game_response.status_code, game_id)
                                await websocket.send_json({"success": False, "detection": detection, "message": "game service unavailable"})
                        except Exception as error:
                            logger.exception("Error sending to Game Service for game %s", game_id)
                            await websocket.send_json(data)
            except Exception as error:
                logger.exception("Error receiving from CV for game %s", game_id)

        asyncio.create_task(receive_from_cv())

        while True:
            frame_data = await websocket.receive_text()
            await cv_ws.send(frame_data)
    except WebSocketDisconnect:
        logger.info("Mobile WebSocket disconnected for game: %s", game_id)
    except Exception as error:
        logger.exception("WebSocket error for game %s", game_id)
    finally:
        if game_id in state.active_connections:
            del state.active_connections[game_id]
        if cv_ws:
            await cv_ws.close()
        if game_id in state.cv_connections:
            del state.cv_connections[game_id]
        logger.info("Cleaned up connections for game: %s", game_id)
