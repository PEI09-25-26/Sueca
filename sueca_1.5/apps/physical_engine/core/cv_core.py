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
    from ..card_mapper import CardMapper
except (ImportError, ValueError):
    from apps.physical_engine.cv.yolo import CornerYoloDetector
    from apps.physical_engine.card_mapper import CardMapper


detector: Optional[CornerYoloDetector] = None
active_games: Dict[str, Dict] = {}
MAX_CARDS_PER_TRICK = 4
EXCLUSION_OVERLAP_THRESHOLD = 0.40
STALE_GAME_TIMEOUT = 3600  # 1 hour


def _cleanup_stale_games():
    """Remove game states that haven't been active for over an hour."""
    now = time.time()
    stale_ids = [
        gid for gid, state in active_games.items()
        if now - state.get("last_active", 0) > STALE_GAME_TIMEOUT
    ]
    for gid in stale_ids:
        del active_games[gid]
        print(f"[CV Core] Cleaned up stale game state: {gid}")


def _build_card_id(rank: str, suit: str) -> Optional[int]:
    suit_map = {"Clubs": "♣", "Diamonds": "♦", "Hearts": "♥", "Spades": "♠"}
    suit_symbol = suit_map.get(suit)
    if not suit_symbol or rank not in CardMapper.RANKS:
        return None

    suit_idx = CardMapper.SUITS.index(suit_symbol)
    rank_idx = CardMapper.RANKS.index(rank)
    return suit_idx * CardMapper.SUITSIZE + rank_idx


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
    - Others: Accepted if confidence >= 0.8 (higher threshold for stability)
    """
    if rank in ("8", "9", "10"):
        return False
    
    if rank == "A":
        return confidence >= 0.5
    
    return confidence >= 0.8


async def start_cv(request: StartCVRequest):
    global detector

    _cleanup_stale_games()
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

        active_games[request.game_id] = {
            "sent_labels": set(),
            "exclusion_zones": [],
            "paused_until": 0.0,
            "trick_count": 0,
            "trick_locked": False,
            "is_paused": False,
            "mode": "trump",  # default to trump detection
            "last_active": time.time(),
            "trump_card": None,
            "frame_consistency": {},  # card_id -> streak_count
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
            "is_paused": False,
            "mode": "trump",
            "last_active": time.time(),
            "trump_card": None,
            "frame_consistency": {},
        }

    try:
        while True:
            message = await websocket.receive_text()

            # Always fetch the latest state objects from the global registry.
            # This ensures that if another request called start_cv() or stop_cv()
            # for this game_id, we pick up the fresh objects and don't use stale ones.
            if game_id not in active_games:
                # If game was stopped, we stop streaming.
                break

            game_state = active_games[game_id]
            game_state["last_active"] = time.time()
            sent_labels: Set[str] = game_state["sent_labels"]
            exclusion_zones: List[Tuple[float, float, float, float]] = game_state["exclusion_zones"]
            frame_consistency: Dict[int, int] = game_state["frame_consistency"]

            if message.startswith("{"):
                try:
                    command = json.loads(message)
                    action = command.get("action")
                    if action == "reset_cards":
                        delay = command.get("delay", 3)
                        full = command.get("full", False)
                        resume = command.get("resume", False)
                        game_state["paused_until"] = time.time() + delay
                        exclusion_zones.clear()
                        frame_consistency.clear()
                        game_state["trick_count"] = 0
                        game_state["trick_locked"] = False
                        if full:
                            sent_labels.clear()
                            # Re-add trump to sent_labels so it's always ignored during play
                            if game_state.get("trump_card"):
                                sent_labels.add(game_state["trump_card"])
                        if resume:
                            game_state["is_paused"] = False

                        await websocket.send_json({
                            "success": True,
                            "message": "cards_reset",
                            "paused_seconds": delay,
                        })
                        print(f"[CV Core] Game {game_id} reset (full={full}, resume={resume})")
                        continue
                    elif action == "pause":
                        game_state["is_paused"] = True
                        await websocket.send_json({"success": True, "message": "paused"})
                        print(f"[CV Core] Game {game_id} paused")
                        continue
                    elif action == "resume":
                        game_state["is_paused"] = False
                        await websocket.send_json({"success": True, "message": "resumed"})
                        print(f"[CV Core] Game {game_id} resumed")
                        continue
                    elif action == "set_mode":
                        new_mode = command.get("mode", "trick")
                        game_state["mode"] = new_mode
                        await websocket.send_json({"success": True, "message": f"mode_set_{new_mode}"})
                        print(f"[CV Core] Game {game_id} mode set to: {new_mode}")
                        continue
                except json.JSONDecodeError:
                    pass

            if game_state.get("is_paused") or time.time() < game_state["paused_until"] or game_state["trick_locked"]:
                continue

            frame = base64_to_image(message)
            if frame is None:
                continue

            detections = detector.detect(frame)
            current_frame_card_ids = set()

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

                card_id = _build_card_id(rank, suit)
                if card_id is None:
                    continue

                label_key = str(card_id) # Using card_id as key instead of rank_suit string
                if label_key not in sent_labels:
                    current_frame_card_ids.add(card_id)

            # Clean up consistency for cards no longer in frame
            keys_to_remove = [cid for cid in frame_consistency if cid not in current_frame_card_ids]
            for cid in keys_to_remove:
                del frame_consistency[cid]

            # Update streaks
            for cid in current_frame_card_ids:
                frame_consistency[cid] = frame_consistency.get(cid, 0) + 1

                if frame_consistency[cid] >= 3:
                    # FOUND A CONSISTENT CARD
                    del frame_consistency[cid]

                    label_key = str(cid)
                    sent_labels.add(label_key)

                    # Find original detection to get bbox and confidence
                    # (In a real scenario, we might want to store more data in streaks)
                    orig_det = next((d for d in detections if _build_card_id(*parse_label(d["label"])) == cid), None)
                    if not orig_det: continue

                    exclusion_zones.append(tuple(orig_det["bbox"]))
                    rank, suit = parse_label(orig_det["label"])

                    detection_result = {
                        "rank": rank,
                        "suit": suit,
                        "card_id": cid,
                        "confidence": orig_det["confidence"],
                    }
                    await websocket.send_json({
                        "success": True,
                        "detection": detection_result,
                    })
                    print(f"[CV Core] Game {game_id}: Detected {rank} of {suit} (ID: {cid})")

                    # Self-pause after trump detection to prevent race conditions
                    if game_state["mode"] == "trump":
                        game_state["is_paused"] = True
                        game_state["trump_card"] = label_key
                        print(f"[CV Core] Game {game_id}: Auto-paused after trump detection")
                        break

                    game_state["trick_count"] += 1
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
    
    # Try to build card_id
    # Ensure suit is capitalized for our map
    suit = request.suit.capitalize()
    # Handle common rank variations
    rank_map = {"king": "K", "queen": "Q", "jack": "J", "ace": "A", "k": "K", "q": "Q", "j": "J", "a": "A", "1": "A"}
    rank = rank_map.get(request.rank.lower(), request.rank.upper())

    cid = _build_card_id(rank, suit)
    if cid is None:
         return {"success": False, "message": f"Invalid card identification: {rank} of {suit}"}

    label_key = str(cid)

    if label_key in game_state["sent_labels"]:
        game_state["sent_labels"].remove(label_key)
        if game_state["trick_count"] > 0:
            game_state["trick_count"] -= 1
        game_state["trick_locked"] = False
        
        # We can't easily know which exclusion zone to pop without more state,
        # but clearing the last one is a reasonable heuristic for the most recent card.
        if game_state["exclusion_zones"]:
            game_state["exclusion_zones"].pop()
            
        print(f"[CV Core] Game {game_id}: Undid card {label_key}")
        return {"success": True, "message": f"Card {label_key} removed from memory"}

    return {"success": False, "message": f"Card {label_key} not in memory. Present: {list(game_state['sent_labels'])}"}


async def health_status():
    _cleanup_stale_games()
    return {
        "status": "healthy",
        "detector_loaded": detector is not None,
        "active_games_count": len(active_games),
        "active_game_ids": list(active_games.keys()),
    }
