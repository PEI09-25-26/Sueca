from typing import Optional
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import json
import os
from pathlib import Path

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

try:
    from cv import CardDetector, CardClassifier
except ImportError:
    from cv.opencv import CardDetector
    from cv.yolo import CardClassifier


detector: Optional[CardDetector] = None
classifier: Optional[CardClassifier] = None
active_games: dict = {}


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
        print(f"[CV Service] Error converting base64 to image: {error}")
        return None


async def start_cv(request: StartCVRequest):
    global detector, classifier

    try:
        detector = CardDetector(debug=False, min_area=10000)

        model_path = resolve_model_path()
        if model_path is not None:
            print(f"[CV Service] YOLO model found: {model_path}")
            classifier = CardClassifier(model_path=model_path)
            print("[CV Service] Classifier initialized successfully")
        else:
            print("[CV Service] No YOLO model found. Only detection will be available.")
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

    except Exception as error:
        print(f"[CV Service] Error starting service: {error}")
        raise HTTPException(status_code=500, detail=str(error))


async def stream_cv(websocket: WebSocket, game_id: str):
    global detector, classifier

    await websocket.accept()
    print(f"[CV Service] WebSocket connected for game: {game_id}")

    if detector is None:
        await websocket.send_json({"error": "CV service not initialized. Call /cv/start first."})
        await websocket.close()
        return

    if game_id not in active_games:
        active_games[game_id] = {
            "last_labels": {},
            "sent_labels": set(),
        }

    game_state = active_games[game_id]
    last_labels = game_state["last_labels"]
    sent_labels = game_state["sent_labels"]

    try:
        while True:
            message = await websocket.receive_text()

            if message.startswith("{"):
                try:
                    command = json.loads(message)
                    if command.get("action") == "reset_cards":
                        print("[CV Service] Received reset command - clearing card history")
                        sent_labels.clear()
                        last_labels.clear()
                        await websocket.send_json({
                            "success": True,
                            "message": "cards_reset",
                        })
                        continue
                except json.JSONDecodeError:
                    pass

            frame_base64 = message

            frame = base64_to_image(frame_base64)
            if frame is None:
                continue

            flatten_cards, _, _ = detector.detect_cards_from_frame(frame)

            if flatten_cards and classifier:
                for i, flat_card in enumerate(flatten_cards):
                    class_label, conf = classifier.classify(flat_card)
                    label_str = f"{class_label} ({conf:.2f})" if class_label else "Unknown"

                    prev_label = last_labels.get(i)
                    if prev_label != label_str and class_label:
                        print(f"[CV Service] Card {i}: {label_str}")
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
                                print(f"[CV Service] New card detected: {rank} of {suit} (confidence: {conf:.2%})")

    except WebSocketDisconnect:
        print(f"[CV Service] WebSocket disconnected for game: {game_id}")
    except Exception as error:
        print(f"[CV Service] Error in WebSocket stream: {error}")
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
