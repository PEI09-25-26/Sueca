import asyncio
import json
import logging

import requests
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import state

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_ws_token(websocket: WebSocket) -> str | None:
    """Extract bearer token from query params or headers."""
    # Try query param first (e.g. ?token=xxx)
    token = websocket.query_params.get("token")
    if token:
        return token
    # Try Authorization header
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return None


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

        # Initialize CV in trump mode
        try:
            await cv_ws.send(json.dumps({"action": "set_mode", "mode": "trump"}))
            print(f"[Middleware] Initialized CV in trump mode for {game_id}")
        except Exception as e:
            print(f"[Middleware] Failed to initialize CV mode: {e}")

        async def receive_from_cv():
            try:
                async for message in cv_ws:
                    data = json.loads(message)
                    if data.get("success") and data.get("detection"):
                        detection = data["detection"]
                        print(f"[Middleware] Received detection from CV: {detection}")

                        try:
                            suit_symbol = state.SUIT_SYMBOLS.get(detection["suit"], detection["suit"])

                            # Ensure sequential processing per game to prevent race conditions/resets
                            if game_id not in state.game_locks:
                                state.game_locks[game_id] = asyncio.Lock()

                            async with state.game_locks[game_id]:
                                max_retries = 2
                                game_response = None
                                for attempt in range(max_retries):
                                    try:
                                        game_response = await asyncio.to_thread(
                                            state.INTERNAL_HTTP.post,
                                            f"{state.GAME_SERVICE_URL}/card",
                                            json={
                                                "game_id": game_id,
                                                "rank": detection["rank"],
                                                "suit": suit_symbol,
                                                "confidence": detection.get("confidence", 1.0),
                                            },
                                            timeout=5,
                                        )
                                        break
                                    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                                        if attempt == max_retries - 1:
                                            raise e
                                        print(f"[Middleware] Retry {attempt+1} for {game_id} due to: {e}")
                                        await asyncio.sleep(0.2)

                            if game_response and game_response.status_code == 200:
                                game_result = game_response.json()
                                print(f"[Middleware] Game Service response: {game_result}")

                                # If trump was just set, reset CV history and PAUSE until start
                                if "message" in game_result and "Trump card set" in game_result["message"]:
                                    try:
                                        # Full reset + Pause
                                        reset_cmd = json.dumps({"action": "reset_cards", "delay": 1, "full": True})
                                        await cv_ws.send(reset_cmd)

                                        pause_cmd = json.dumps({"action": "pause"})
                                        await cv_ws.send(pause_cmd)

                                        print(f"[Middleware] Reset and PAUSED CV history after trump detection for {game_id}")
                                    except Exception as e:
                                        print(f"[Middleware] Failed to send pause/reset to CV: {e}")

                                # Auto-reset for normal tricks when trick ends
                                elif game_result.get("queue_size") == 0:
                                    try:
                                        async def delayed_reset():
                                            await asyncio.sleep(1.5)
                                            try:
                                                reset_cmd = json.dumps({"action": "reset_cards", "delay": 2, "resume": True})
                                                await cv_ws.send(reset_cmd)
                                                print(f"[Middleware] Auto-reset CV after trick for {game_id}")
                                            except Exception:
                                                pass
                                        asyncio.create_task(delayed_reset())
                                    except Exception as e:
                                        print(f"[Middleware] Failed to schedule auto-reset: {e}")

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


@router.websocket("/ws/hybrid/{game_id}")
async def websocket_hybrid(websocket: WebSocket, game_id: str):
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4001)
        logger.warning("Missing token for hybrid WS game %s", game_id)
        return
        
    await websocket.accept()
    if game_id not in state.hybrid_stream_connections:
        state.hybrid_stream_connections[game_id] = []
    state.hybrid_stream_connections[game_id].append(websocket)
    logger.info("Hybrid WebSocket connected for game: %s (Total: %d)", game_id, len(state.hybrid_stream_connections[game_id]))

    async def _push_initial_snapshot():
        """Send latest game/hybrid state so clients recover after WS reconnect."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            status_response = await asyncio.to_thread(
                state.INTERNAL_HTTP.get,
                f"{state.HYBRID_ENGINE_URL}/api/status",
                params={"game_id": game_id},
                headers=headers,
                timeout=5,
            )
            hybrid_state_response = await asyncio.to_thread(
                state.INTERNAL_HTTP.get,
                f"{state.HYBRID_ENGINE_URL}/api/hybrid/state",
                params={"game_id": game_id},
                headers=headers,
                timeout=5,
            )
            if not status_response.ok and not hybrid_state_response.ok:
                return
            status_json = status_response.json() if status_response.ok else {}
            hybrid_json = hybrid_state_response.json() if hybrid_state_response.ok else {}
            snapshot = {"type": "state_update"}
            if status_response.ok:
                snapshot["game_state"] = status_json
            if hybrid_state_response.ok:
                snapshot["hybrid_state"] = hybrid_json.get("state")
            await websocket.send_text(json.dumps(snapshot))
        except Exception as exc:
            logger.warning("Failed to push hybrid WS snapshot for %s: %s", game_id, exc)

    asyncio.create_task(_push_initial_snapshot())

    try:
        while True:
            # We must wait for either text (JSON actions) or bytes (camera frames)
            message = await websocket.receive()
            if "bytes" in message:
                # Raw binary camera frame. Broadcast to other clients.
                frame_data = message["bytes"]
                for client in state.hybrid_stream_connections[game_id]:
                    if client != websocket:
                        try:
                            await client.send_bytes(frame_data)
                        except Exception as e:
                            logger.error("Error broadcasting binary frame: %s", e)
            elif "text" in message:
                # JSON Action
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "action" and "action" in data:
                        action_name = data["action"]
                        payload = data.get("payload", {})
                        # Ensure game_id is in payload
                        payload["game_id"] = game_id

                        if action_name == "sync_state":
                            status_response = await asyncio.to_thread(
                                state.INTERNAL_HTTP.get,
                                f"{state.HYBRID_ENGINE_URL}/api/status",
                                params={"game_id": game_id},
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=5,
                            )
                            hybrid_state_response = await asyncio.to_thread(
                                state.INTERNAL_HTTP.get,
                                f"{state.HYBRID_ENGINE_URL}/api/hybrid/state",
                                params={"game_id": game_id},
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=5,
                            )

                            status_json = status_response.json() if status_response.ok else {}
                            hybrid_json = hybrid_state_response.json() if hybrid_state_response.ok else {}
                            resp_json = {
                                "success": status_response.ok and hybrid_state_response.ok,
                                "game_state": status_json,
                                "state": hybrid_json.get("state"),
                            }
                            response_status = 200 if resp_json["success"] else 502
                        else:
                            action_map = {
                                "register_player": f"{state.HYBRID_ENGINE_URL}/api/hybrid/register_player",
                                "deal_reset": f"{state.HYBRID_ENGINE_URL}/api/hybrid/deal/reset",
                                "deal_finalize": f"{state.HYBRID_ENGINE_URL}/api/hybrid/deal/finalize",
                                "trump_confirm_capture": f"{state.HYBRID_ENGINE_URL}/api/hybrid/trump/confirm_capture",
                                "deal_recognize": f"{state.HYBRID_ENGINE_URL}/api/hybrid/deal/recognize",
                                "virtual_select_card": f"{state.HYBRID_ENGINE_URL}/api/hybrid/virtual/select_card",
                                "play_confirm_capture": f"{state.HYBRID_ENGINE_URL}/api/hybrid/play/confirm_capture",
                                "play_undo": f"{state.HYBRID_ENGINE_URL}/api/hybrid/play/undo",
                                "confirm_trick": f"{state.HYBRID_ENGINE_URL}/api/hybrid/play/confirm_trick",
                                "play_force_renuncia": f"{state.HYBRID_ENGINE_URL}/api/hybrid/play/force_renuncia",
                                "select_trump": f"{state.HYBRID_ENGINE_URL}/api/select_trump",
                            }
                            endpoint = action_map.get(action_name)
                            if endpoint is None:
                                raise ValueError(f"Unsupported hybrid WS action: {action_name}")

                            response = await asyncio.to_thread(
                                state.INTERNAL_HTTP.post,
                                endpoint,
                                json=payload,
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=5,
                            )
                            response_status = response.status_code

                            try:
                                resp_json = response.json()
                            except ValueError:
                                resp_json = {"success": False, "message": "Invalid response from hybrid engine"}
                            
                        # Send the response directly to the caller
                        resp_envelope = {
                            "type": "action_response",
                            "action": action_name,
                            "response": resp_json
                        }
                        await websocket.send_json(resp_envelope)
                        
                        # If action was successful and returned state updates, broadcast to all
                        if response_status == 200 and resp_json.get("success"):
                            broadcast_payload = {
                                "type": "state_update"
                            }
                            if "state" in resp_json:
                                broadcast_payload["hybrid_state"] = resp_json["state"]
                            if "game_state" in resp_json:
                                broadcast_payload["game_state"] = resp_json["game_state"]
                                
                            if "hybrid_state" in broadcast_payload or "game_state" in broadcast_payload:
                                for client in state.hybrid_stream_connections[game_id]:
                                    try:
                                        await client.send_json(broadcast_payload)
                                    except Exception as e:
                                        logger.error("Error broadcasting state: %s", e)
                                        
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON on hybrid websocket")
                except Exception as e:
                    logger.error("Error handling hybrid action: %s", e)

    except WebSocketDisconnect:
        logger.info("Hybrid WebSocket disconnected for game: %s", game_id)
    except Exception as error:
        logger.error("Hybrid WebSocket error: %s", error)
    finally:
        if game_id in state.hybrid_stream_connections:
            if websocket in state.hybrid_stream_connections[game_id]:
                state.hybrid_stream_connections[game_id].remove(websocket)
            if not state.hybrid_stream_connections[game_id]:
                del state.hybrid_stream_connections[game_id]
        logger.info("Cleaned up hybrid connection for game: %s", game_id)
