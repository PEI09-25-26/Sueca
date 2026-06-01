from typing import Optional, Dict, List, Set, Tuple
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import json
import os
import time
from pathlib import Path

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

try:
    # Use the improved detector from the local cv module
    from ..cv.yolo import CornerYoloDetector
except (ImportError, ValueError):
    from apps.physical_engine.cv.yolo import CornerYoloDetector


detector: Optional[CornerYoloDetector] = None
active_games: Dict[str, Dict] = {}
MAX_CARDS_PER_TRICK = 4
EXCLUSION_OVERLAP_THRESHOLD = 0.40


def resolve_model_path() -> Optional[str]:
    """Resolve the detection model path using env override and known locations."""
    physical_engine_root = Path(__file__).resolve().parents[1]

    env_model = os.getenv("CV2_MODEL_PATH", "").strip()
    candidate_paths: list[Path] = []
    if env_model:
        env_path = Path(env_model)
        candidate_paths.append(env_path)
        if not env_path.is_absolute():
            candidate_paths.append(physical_engine_root / env_path)

    candidate_paths.extend(
        [
            physical_engine_root / "cv" / "best.pt",
            physical_engine_root / "runs" / "detect" / "corner_cards" / "weights" / "best.pt",
            physical_engine_root / "runs" / "detect" / "train" / "weights" / "best.pt",
        ]
    )

    for path in candidate_paths:
        if path.exists() and path.is_file():
            return str(path)
    return None


class StartCVRequest(BaseModel):
    game_id: str


class UndoCardRequest(BaseModel):
    game_id: str
    rank: str
    suit: str


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
    return rank, suit


def bbox_overlap_ratio(box_new: List[float], box_existing: Tuple[float, float, float, float]) -> float:
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


def base64_to_image(base64_string: str) -> Optional[np.ndarray]:
    try:
        img_data = base64.b64decode(base64_string)
        pil_image = Image.open(BytesIO(img_data)).convert("RGB")
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return opencv_image
    except Exception as error:
        print(f"[CV Core] Error converting base64 to image: {error}")
        return None


def should_accept_card(rank: str, suit: str, confidence: float) -> bool:
    """
    Selectively filter cards based on rank and confidence.
    - Cards 8, 9, 10: Never accepted (not used in Sueca)
    - Aces: Accepted if confidence >= 0.5 (difficult to recognize)
    - Others: Accepted if confidence >= 0.6 (standard threshold)
    """
    if rank in ("8", "9", "10"):
        return False
    
    if rank == "A":
        return confidence >= 0.5
    
    return confidence >= 0.6


async def start_cv(request: StartCVRequest):
    global detector

    try:
        model_path = resolve_model_path()
        if model_path is None:
            raise HTTPException(
                status_code=500,
                detail="No detection model found. Set CV2_MODEL_PATH or check 'cv/' directory."
            )

        if detector is None:
            detector = CornerYoloDetector(model_path=model_path)
            print(f"[CV Core] Detector initialized with model: {model_path}")

        if request.game_id not in active_games:
            active_games[request.game_id] = {
                "sent_labels": set(),
                "exclusion_zones": [],
                "paused_until": 0.0,
                "trick_count": 0,
                "trick_locked": False,
            }

        return {
            "success": True,
            "message": "CV service started successfully",
            "game_id": request.game_id,
        }

    except HTTPException:
        raise
    except Exception as error:
        print(f"[CV Core] Error starting service: {error}")
        raise HTTPException(status_code=500, detail=str(error))


async def stream_cv(websocket: WebSocket, game_id: str):
    global detector

    await websocket.accept()
    print(f"[CV Core] WebSocket connected for game: {game_id}")

    if detector is None:
        model_path = resolve_model_path()
        if model_path is None:
            await websocket.send_json({"error": "CV model not found."})
            await websocket.close()
            return
        detector = CornerYoloDetector(model_path=model_path)

    if game_id not in active_games:
        active_games[game_id] = {
            "sent_labels": set(),
            "exclusion_zones": [],
            "paused_until": 0.0,
            "trick_count": 0,
            "trick_locked": False,
        }

    game_state = active_games[game_id]
    sent_labels: Set[str] = game_state["sent_labels"]
    exclusion_zones: List[Tuple[float, float, float, float]] = game_state["exclusion_zones"]

    try:
        while True:
            message = await websocket.receive_text()

            if message.startswith("{"):
                try:
                    command = json.loads(message)
                    if command.get("action") == "reset_cards":
                        delay = command.get("delay", 3)
                        full = command.get("full", False)
                        game_state["paused_until"] = time.time() + delay
                        exclusion_zones.clear()
                        game_state["trick_count"] = 0
                        game_state["trick_locked"] = False
                        if full:
                            sent_labels.clear()
                        
                        await websocket.send_json({
                            "success": True,
                            "message": "cards_reset",
                            "paused_seconds": delay,
                        })
                        print(f"[CV Core] Game {game_id} reset (full={full})")
                        continue
                except json.JSONDecodeError:
                    pass

            if time.time() < game_state["paused_until"] or game_state["trick_locked"]:
                continue

            frame = base64_to_image(message)
            if frame is None:
                continue

            detections = detector.detect(frame)

            for i, det in enumerate(detections):
                bbox = det["bbox"]

                # Skip if detection overlaps significantly with an already detected card in this trick
                skip = False
                for zone in exclusion_zones:
                    if bbox_overlap_ratio(bbox, zone) >= EXCLUSION_OVERLAP_THRESHOLD:
                        skip = True
                        break
                if skip:
                    continue

                rank, suit = parse_label(det["label"])
                if rank is None or suit is None:
                    continue

                if not should_accept_card(rank, suit, det["confidence"]):
                    continue

                card_key = f"{rank}_{suit}"
                if card_key not in sent_labels:
                    sent_labels.add(card_key)
                    exclusion_zones.append(tuple(bbox))
                    game_state["trick_count"] += 1

                    detection_result = {
                        "rank": rank,
                        "suit": suit,
                        "confidence": det["confidence"],
                        "position": i,
                    }
                    await websocket.send_json({
                        "success": True,
                        "detection": detection_result,
                    })
                    print(f"[CV Core] Game {game_id}: Detected {rank} of {suit}")

                    if game_state["trick_count"] >= MAX_CARDS_PER_TRICK:
                        game_state["trick_locked"] = True
                        print(f"[CV Core] Game {game_id}: Trick locked (4 cards)")
                        break

    except WebSocketDisconnect:
        print(f"[CV Core] WebSocket disconnected for game: {game_id}")
    except Exception as error:
        print(f"[CV Core] Error in WebSocket stream for {game_id}: {error}")
        await websocket.close()


async def stop_cv(game_id: str):
    if game_id in active_games:
        del active_games[game_id]
        return {"success": True, "message": "CV game state cleared"}
    return {"success": False, "message": "Game not found"}


async def undo_card(request: UndoCardRequest):
    game_id = request.game_id
    if game_id not in active_games:
        # Fallback to default if specific game not found (legacy behavior)
        game_id = "default" if "default" in active_games else game_id
    
    if game_id not in active_games:
        return {"success": False, "message": f"Game {game_id} not active"}

    game_state = active_games[game_id]
    
    # Map input rank to standard YOLO labels
    rank_map = {"king": "K", "queen": "Q", "jack": "J", "ace": "A", "k": "K", "q": "Q", "j": "J", "a": "A"}
    r = rank_map.get(request.rank.lower(), request.rank)
    s = request.suit.capitalize()
    card_key = f"{r}_{s}"

    found_key = None
    if card_key in game_state["sent_labels"]:
        found_key = card_key
    else:
        # Case-insensitive search
        for sk in list(game_state["sent_labels"]):
            if sk.lower() == card_key.lower():
                found_key = sk
                break

    if found_key:
        game_state["sent_labels"].remove(found_key)
        if game_state["trick_count"] > 0:
            game_state["trick_count"] -= 1
        game_state["trick_locked"] = False
        
        # We can't easily know which exclusion zone to pop without more state,
        # but clearing the last one is a reasonable heuristic for the most recent card.
        if game_state["exclusion_zones"]:
            game_state["exclusion_zones"].pop()
            
        print(f"[CV Core] Game {game_id}: Undid card {found_key}")
        return {"success": True, "message": f"Card {found_key} removed from memory"}

    return {"success": False, "message": f"Card {card_key} not in memory"}


async def health_status():
    return {
        "status": "healthy",
        "detector_loaded": detector is not None,
        "active_games_count": len(active_games),
        "active_game_ids": list(active_games.keys()),
    }
