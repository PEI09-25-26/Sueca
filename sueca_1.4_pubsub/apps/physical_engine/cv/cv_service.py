from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Optional
import base64
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import json
import os
import time
import logging

from apps.virtual_engine.session import session_manager

try:
    from .yolo import CornerYoloDetector
except ImportError:
    from yolo import CornerYoloDetector


app = FastAPI(title="Computer Vision Service", version="2.0")


detector: Optional[CornerYoloDetector] = None
active_games: Dict[str, Dict] = {}
MAX_CARDS_PER_TRICK = 4
logger = logging.getLogger("physical_engine.cv")


class StartCVRequest(BaseModel):
    game_id: str


def parse_label(label: str):
    if len(label) < 2:
        return None, None

    rank = label[:-1]
    suit_char = label[-1].lower()
    suit_map = {
        "c": "Clubs",
        "d": "Diamonds",
        "h": "Hearts",
        "s": "Spades",
    }
    suit = suit_map.get(suit_char)
    if suit is None:
        return None, None

    return rank, suit


def bbox_overlap_ratio(box_new, box_existing):
    ax1, ay1, ax2, ay2 = box_new
    bx1, by1, bx2, by2 = box_existing

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter_area = (ix2 - ix1) * (iy2 - iy1)
    area_new = (ax2 - ax1) * (ay2 - ay1)
    if area_new <= 0:
        return 0.0

    return inter_area / area_new


def base64_to_image(base64_string: str):
    try:
        img_data = base64.b64decode(base64_string)
        pil_image = Image.open(BytesIO(img_data)).convert("RGB")
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    except Exception as exc:
        print(f"[CV2] Failed to decode frame: {exc}")
        return None


def resolve_model_path() -> Optional[str]:
    env_path = os.getenv("CV2_MODEL_PATH")
    candidates = []
    if env_path:
        candidates.append(env_path)

    candidates.extend(
        [
            "./apps/physical_engine/cv/best.pt",
            "/app/apps/physical_engine/cv/best.pt",
            os.path.join(os.path.dirname(__file__), "best.pt"),
            "./runs/archive3_final/weights/best.pt",
            "./runs/detect/corner_cards/weights/best.pt",
            "./runs/detect/train/weights/best.pt",
            "../ComputerVision_1.0/runs/detect/train/weights/best.pt",
        ]
    )

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    return None


EXCLUSION_OVERLAP_THRESHOLD = 0.40


@app.post("/cv/start", responses={500: {"description": "Internal server error"}})
async def start_cv_service(request: StartCVRequest):
    global detector

    try:
        model_path = resolve_model_path()
        if model_path is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "No detection model found. Set CV2_MODEL_PATH or place a model in "
                    "runs/detect/.../best.pt"
                ),
            )

        detector = CornerYoloDetector(model_path=model_path)

        active_games[request.game_id] = {
            "sent_labels": set(),
            "exclusion_zones": [],
            "paused_until": 0,
            "trick_count": 0,
            "trick_locked": False,
            "frames_received": 0,
        }

        return {
            "success": True,
            "message": "CV 2.0 service started successfully",
            "model_path": model_path,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[CV2] Error starting service: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


def _ensure_game_state(game_id: str) -> Dict:
    if game_id not in active_games:
        active_games[game_id] = {
            "sent_labels": set(),
            "exclusion_zones": [],
            "paused_until": 0,
            "trick_count": 0,
            "trick_locked": False,
            "frames_received": 0,
        }
    return active_games[game_id]


def _handle_control_message(command: Dict, game_state: Dict, sent_labels, exclusion_zones) -> bool:
    if command.get("action") == "reset_cards":
        delay = command.get("delay", 3)
        full = command.get("full", False)
        game_state["paused_until"] = time.time() + delay
        exclusion_zones.clear()
        game_state["trick_count"] = 0
        game_state["trick_locked"] = False
        if full:
            sent_labels.clear()
        return True

    if command.get("action") == "correct_card":
        wrong_label = command.get("wrong_label")
        if wrong_label:
            sent_labels.discard(wrong_label)
        return True

    return False


async def _emit_control_ack(websocket: WebSocket, command: Dict):
    if command.get("action") == "reset_cards":
        await websocket.send_json(
            {
                "success": True,
                "message": "cards_reset",
                "paused_seconds": command.get("delay", 3),
            }
        )
        return

    if command.get("action") == "correct_card":
        await websocket.send_json(
            {
                "success": True,
                "message": "card_corrected",
                "wrong_label": command.get("wrong_label"),
                "correct_label": command.get("correct_label"),
            }
        )


async def _process_detections(frame, game_state: Dict, sent_labels, exclusion_zones, websocket: WebSocket):
    detections = detector.detect(frame)
    for i, det in enumerate(detections):
        bbox = det["bbox"]

        skip = False
        for zone in exclusion_zones:
            overlap = bbox_overlap_ratio(bbox, zone)
            if overlap >= EXCLUSION_OVERLAP_THRESHOLD:
                skip = True
                break
        if skip:
            continue

        rank, suit = parse_label(det["label"])
        if rank is None or suit is None:
            continue

        class_label = det["label"]
        if class_label in sent_labels:
            continue

        sent_labels.add(class_label)
        exclusion_zones.append(tuple(bbox))
        game_state["trick_count"] += 1

        detection = {
            "rank": rank,
            "suit": suit,
            "confidence": det["confidence"],
            "position": i,
        }
        await websocket.send_json({"success": True, "detection": detection})
        print(
            f"[CV2] New card detected: {rank} of {suit} "
            f"(confidence: {det['confidence']:.2%})"
        )

        if game_state["trick_count"] >= MAX_CARDS_PER_TRICK:
            game_state["trick_locked"] = True
            print("[CV2] Trick locked after 4 cards. Waiting for reset_cards.")
            break


async def _handle_stream_message(message: str, game_state: Dict, sent_labels, exclusion_zones, websocket: WebSocket):
    if message.startswith("{"):
        try:
            command = json.loads(message)
            if _handle_control_message(command, game_state, sent_labels, exclusion_zones):
                await _emit_control_ack(websocket, command)
                return
        except json.JSONDecodeError:
            pass

    frame = base64_to_image(message)
    if frame is None:
        return

    if time.time() < game_state["paused_until"]:
        return

    if game_state["trick_locked"]:
        return

    await _process_detections(frame, game_state, sent_labels, exclusion_zones, websocket)


@app.websocket("/cv/stream/{game_id}")
async def cv_stream(websocket: WebSocket, game_id: str):
    global detector

    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4001)
        print(f"[CV2] Missing token for game: {game_id}")
        return

    payload = session_manager.validate_token(token)
    if not payload:
        # Fallback for short-lived game tokens (which aren't tracked in session_manager memory)
        try:
            from apps.virtual_engine.session import decode_session_token
            payload = decode_session_token(token)
            if not payload.get("game_id"):
                payload = None
        except Exception:
            payload = None

    if not payload:
        await websocket.close(code=4002)
        print(f"[CV2] Token validation failed for game: {game_id}")
        return

    if payload.get("game_id") != game_id:
        await websocket.close(code=4003)
        print(f"[CV2] Token game_id mismatch for game: {game_id}")
        return

    await websocket.accept()
    print(f"[CV2] WebSocket connected for game: {game_id}")

    if detector is None:
        await websocket.send_json({"error": "CV service not initialized. Call /cv/start first."})
        await websocket.close()
        return

    game_state = _ensure_game_state(game_id)
    sent_labels = game_state["sent_labels"]
    exclusion_zones = game_state["exclusion_zones"]

    try:
        while True:
            message = await websocket.receive_text()
            game_state["frames_received"] += 1

            if game_state["frames_received"] % 30 == 0:
                logger.debug("Frame batch received: total_frames=%s", game_state["frames_received"])

            if game_state["frames_received"] % 100 == 0:
                logger.debug("Frame %s received for %s", game_state["frames_received"], game_id)

            await _handle_stream_message(message, game_state, sent_labels, exclusion_zones, websocket)

    except WebSocketDisconnect:
        print(f"[CV2] WebSocket disconnected for game: {game_id}")
    except Exception as exc:
        print(f"[CV2] Error in WebSocket stream: {exc}")
        await websocket.close()


@app.post("/cv/stop")
async def stop_cv_service(game_id: str):
    if game_id in active_games:
        del active_games[game_id]
        return {"success": True, "message": "CV service stopped"}
    return {"success": False, "message": "Game not found"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "detector_loaded": detector is not None,
        "active_games": len(active_games),
        "version": "2.0",
    }
