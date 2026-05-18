from typing import Optional
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import json
import os
import logging
from pathlib import Path

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from apps.virtual_engine.session import session_manager

try:
    from cv import CardDetector, CardClassifier
except ImportError:
    from ..cv.opencv import CardDetector
    from ..cv.yolo import CardClassifier


detector: Optional[CardDetector] = None
classifier: Optional[CardClassifier] = None
active_games: dict = {}

logger = logging.getLogger("physical_engine.cv")


def resolve_model_path() -> Optional[str]:
    """Resolve the classifier model path using env override and known locations."""
    physical_engine_root = Path(__file__).resolve().parents[1]

    env_model = os.getenv("SUECA_YOLO_MODEL_PATH", "").strip()
    candidate_paths: list[Path] = []
    if env_model:
        env_path = Path(env_model)
        candidate_paths.append(env_path)
        if not env_path.is_absolute():
            candidate_paths.append(physical_engine_root / env_path)

    candidate_paths.extend(
        [
            physical_engine_root / "runs" / "classify" / "sueca_cards_classifier" / "weights" / "best.pt",
            physical_engine_root / "runs" / "classify" / "sueca_cards_classifier" / "weights" / "last.pt",
        ]
    )

    for path in candidate_paths:
        if path.exists() and path.is_file():
            return str(path)
    return None


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
    suit = suit_map.get(suit_char, "Unknown")
    return rank, suit


def base64_to_image(base64_string: str) -> Optional[np.ndarray]:
    try:
        img_data = base64.b64decode(base64_string)
        pil_image = Image.open(BytesIO(img_data))
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return opencv_image
    except Exception as error:
        logger.exception("Error converting base64 to image")
        return None


async def start_cv(request: StartCVRequest):
    global detector, classifier

    try:
        detector = CardDetector(debug=False, min_area=10000)

        model_path = resolve_model_path()
        if model_path is not None:
            logger.info("YOLO model found: %s", model_path)
            classifier = CardClassifier(model_path=model_path)
            logger.info("Classifier initialized successfully")
        else:
            logger.info("No YOLO model found. Only detection will be available.")
            classifier = None

        active_games[request.game_id] = {
            "last_labels": {},
            "sent_labels": set(),
        }

        return {
            "success": True,
            "message": "CV service started successfully",
            "has_classifier": classifier is not None,
        }

    except Exception:
        logger.exception("Error starting CV service")
        # Log and return generic error to callers to avoid leaking internals
        raise HTTPException(status_code=500, detail="internal error")


async def stream_cv(websocket: WebSocket, game_id: str):
    global detector, classifier

    authorization = websocket.headers.get("authorization")
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    # Do not accept tokens via query parameters for WebSocket connections.
    secret = os.getenv("SUECA_JWT_SECRET")
    if not token:
        await websocket.close(code=4001)
        logger.warning("Missing token for game: %s", game_id)
        return
    if not secret:
        logger.error("Server misconfigured: missing SUECA_JWT_SECRET")
        await websocket.close(code=4002)
        return

    # Validate via session manager so revocation is respected across services
    payload = session_manager.validate_token(token)
    if not payload:
        logger.warning("Token validation failed for game: %s", game_id)
        await websocket.close(code=4002)
        return

    if payload.get("game_id") != game_id:
        await websocket.close(code=4003)
        logger.warning("Token game_id mismatch for game: %s", game_id)
        return

    await websocket.accept()
    logger.info("WebSocket connected for game: %s", game_id)

    if detector is None:
        await websocket.send_json({"error": "CV service not initialized. Call /cv/start first."})
        await websocket.close()
        return

    if game_id not in active_games:
        active_games[game_id] = {
            "last_labels": {},
            "sent_labels": set(),
            "frames_received": 0,
            "frames_decoded": 0,
            "frames_with_cards": 0,
        }

    game_state = active_games[game_id]
    game_state.setdefault("last_labels", {})
    game_state.setdefault("sent_labels", set())
    game_state.setdefault("frames_received", 0)
    game_state.setdefault("frames_decoded", 0)
    game_state.setdefault("frames_with_cards", 0)
    last_labels = game_state["last_labels"]
    sent_labels = game_state["sent_labels"]

    try:
        while True:
            message = await websocket.receive_text()
            game_state["frames_received"] += 1

            if message.startswith("{"):
                try:
                    command = json.loads(message)
                    if command.get("action") == "reset_cards":
                        logger.info("Received reset command - clearing card history for %s", game_id)
                        sent_labels.clear()
                        last_labels.clear()
                        await websocket.send_json({
                            "success": True,
                            "message": "cards_reset",
                        })
                        logger.info("Reset complete - ready for new frames for %s", game_id)
                        continue
                except json.JSONDecodeError:
                    pass

            # Log frame arrival every 30 frames for debugging
            if game_state["frames_received"] % 30 == 0:
                logger.debug("Frame batch received: total_frames=%s", game_state['frames_received'])

            frame_base64 = message

            frame = base64_to_image(frame_base64)
            if frame is None:
                if game_state["frames_received"] % 100 == 0:
                    logger.warning("Warning: received frame %s was None after decode", game_state['frames_received'])
                continue
            game_state["frames_decoded"] += 1

            flatten_cards, _, _ = detector.detect_cards_from_frame(frame)
            if flatten_cards:
                game_state["frames_with_cards"] += 1
            
            # Log detection attempts every 30 frames
            if game_state["frames_received"] % 30 == 0:
                print(
                    f"[CV Service] Detection check: frame={game_state['frames_received']} "
                    f"cards_found={len(flatten_cards) if flatten_cards else 0} "
                    f"sent_labels={sent_labels} last_labels={last_labels}"
                )

            if flatten_cards and classifier:
                # Debug: log when we have cards to classify
                if game_state["frames_received"] < 750:
                    logger.debug("Frame %s: Found %s cards, about to classify...", game_state['frames_received'], len(flatten_cards))
                
                for i, flat_card in enumerate(flatten_cards):
                    try:
                        class_label, conf = classifier.classify(flat_card)
                        # Log card classification attempts for debugging
                        if game_state["frames_received"] < 750:
                            logger.debug("Frame %s, Card %s: class_label=%s, conf=%.2f, sent_labels=%s", game_state['frames_received'], i, class_label, conf, sent_labels)
                    except Exception as e:
                        logger.exception("Error classifying card %s in game %s", i, game_id)
                        class_label, conf = None, 0.0
                    
                    label_str = f"{class_label} ({conf:.2f})" if class_label else "Unknown"

                    prev_label = last_labels.get(i)
                    if prev_label != label_str and class_label:
                        logger.debug("Card %s: %s", i, label_str)
                        last_labels[i] = label_str

                        if class_label not in sent_labels:
                            rank, suit = parse_label(class_label)
                            if rank and suit:
                                detection = {
                                    "rank": rank,
                                    "suit": suit,
                                    "confidence": conf,
                                    "position": i,
                                }
                                await websocket.send_json({
                                    "success": True,
                                    "detection": detection,
                                })
                                sent_labels.add(class_label)
                                logger.info("New card detected for %s: %s of %s (confidence: %.2f)", game_id, rank, suit, conf)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for game: %s", game_id)
    except Exception:
        logger.exception("CRITICAL ERROR in WebSocket stream for game: %s", game_id)
        await websocket.close()


async def stop_cv(game_id: str):
    if game_id in active_games:
        del active_games[game_id]
        return {"success": True, "message": "CV service stopped"}
    return {"success": False, "message": "Game not found"}


async def health_status():
    return {
        "status": "healthy",
        "detector_loaded": detector is not None,
        "classifier_loaded": classifier is not None,
        "active_games": len(active_games),
    }
