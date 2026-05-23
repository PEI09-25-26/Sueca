"""Local hybrid vision service — card recognition inside the hybrid engine process."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
import base64
import os
from io import BytesIO
from pathlib import Path
from typing import Optional
import logging

from apps.hybrid_engine.card_mapper import CardMapper

logger = logging.getLogger(__name__)


@dataclass
class RecognizedCard:
    card_id: int
    rank: str
    suit_symbol: str
    suit_name: str
    drawable_key: str
    display: str


class HybridVisionService:
    def __init__(self, timeout_s: float = 1.6) -> None:
        self.timeout_s = max(0.5, float(timeout_s))
        self.model_path = self._resolve_model_path()
        self.detector = None
        self._seen_labels_by_game: dict[str, set[str]] = {}

    def _resolve_model_path(self) -> Optional[str]:
        env_path = os.getenv("HYBRID_CV_MODEL_PATH") or os.getenv("CV2_MODEL_PATH")
        candidates = []
        if env_path:
            candidates.append(Path(env_path))

        base_dir = Path(__file__).resolve().parents[1]
        candidates.extend(
            [
                base_dir / "cv" / "best.pt",
                Path("/app/apps/hybrid_engine/cv/best.pt"),
                Path("./apps/hybrid_engine/cv/best.pt"),
            ]
        )

        for path in candidates:
            if path.exists():
                return str(path)
        return None

    def _ensure_started(self) -> bool:
        if self.detector is not None:
            return True
        if not self.model_path:
            logger.error(
                "No hybrid CV model found. Set HYBRID_CV_MODEL_PATH or place best.pt in apps/hybrid_engine/cv/"
            )
            return False
        try:
            from apps.hybrid_engine.cv.yolo import CornerYoloDetector

            self.detector = CornerYoloDetector(model_path=self.model_path)
            return True
        except Exception as exc:
            logger.exception("Failed to load hybrid CV model: %s", exc)
            return False

    async def recognize_once(
        self, game_id: str, frame_base64: str, reset_before: bool = True
    ) -> Optional[RecognizedCard]:
        if reset_before:
            self._seen_labels_by_game.setdefault(game_id, set())

        if not self._ensure_started():
            return None

        frame = self._base64_to_image(frame_base64)
        if frame is None:
            return None

        return await asyncio.to_thread(self._recognize_frame, game_id, frame)

    def _recognize_frame(self, game_id: str, frame) -> Optional[RecognizedCard]:
        detections = self.detector.detect(frame) if self.detector else []
        seen_labels = self._seen_labels_by_game.setdefault(game_id, set())

        for detection in detections:
            label = str(detection.get("label", ""))
            rank, suit = self._parse_label(label)
            if not rank or not suit:
                continue
            if label in seen_labels:
                continue
            if not self._should_accept_card(rank, float(detection.get("confidence", 0.0))):
                continue

            seen_labels.add(label)
            recognized = self._build_from_detection(
                {
                    "rank": rank,
                    "suit": suit,
                    "confidence": detection.get("confidence"),
                }
            )
            if recognized:
                logger.info("Detected card locally: %s (game: %s)", recognized.display, game_id)
                return recognized

        return None

    async def reset_cv_history(self, game_id: str) -> None:
        """Reset local recognition history for a clean start of the playing phase."""
        self._seen_labels_by_game[game_id] = set()
        logger.info("Hybrid CV history reset for game %s", game_id)

    async def test_cv_service(self) -> bool:
        """Verify that a local detector model is configured (loaded lazily on first capture)."""
        return self.model_path is not None

    def _base64_to_image(self, frame_base64: str):
        try:
            import cv2
            import numpy as np
            from PIL import Image

            if "," in frame_base64:
                frame_base64 = frame_base64.split(",", 1)[1]
            img_data = base64.b64decode(frame_base64)
            pil_image = Image.open(BytesIO(img_data)).convert("RGB")
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.warning("Failed to decode hybrid CV frame: %s", exc)
            return None

    def _parse_label(self, label: str):
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
        return rank, suit_map.get(suit_char)

    def _should_accept_card(self, rank: str, confidence: float) -> bool:
        if rank in ("8", "9", "10"):
            return False
        if rank == "A":
            return confidence >= 0.5
        return confidence >= 0.6

    def _build_from_detection(self, detection: dict) -> Optional[RecognizedCard]:
        rank = self._normalize_rank(str(detection.get("rank", "")).strip())
        suit_name = self._normalize_suit(str(detection.get("suit", "")).strip())
        if not rank or not suit_name:
            return None

        suit_symbol = self._suit_symbol(suit_name)
        if suit_symbol is None:
            return None

        if rank not in CardMapper.RANKS:
            return None

        suit_index = CardMapper.SUITS.index(suit_symbol)
        rank_index = CardMapper.RANKS.index(rank)
        card_id = suit_index * CardMapper.SUITSIZE + rank_index

        drawable_rank = rank.lower()
        if drawable_rank == "k":
            drawable_rank = "king"
        elif drawable_rank == "q":
            drawable_rank = "queen"
        elif drawable_rank == "j":
            drawable_rank = "jack"
        elif drawable_rank == "a":
            drawable_rank = "ace"

        drawable_key = f"{self._drawable_suit(suit_name)}_{drawable_rank}"

        return RecognizedCard(
            card_id=card_id,
            rank=rank,
            suit_symbol=suit_symbol,
            suit_name=suit_name,
            drawable_key=drawable_key,
            display=f"{rank}{suit_symbol}",
        )

    def _normalize_rank(self, raw: str) -> Optional[str]:
        if not raw:
            return None

        rank_alias = {
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7",
            "10": "10",
            "j": "J",
            "jack": "J",
            "q": "Q",
            "queen": "Q",
            "k": "K",
            "king": "K",
            "a": "A",
            "ace": "A",
        }

        key = raw.strip().lower()
        return rank_alias.get(key) or rank_alias.get(key[:1])

    def _normalize_suit(self, raw: str) -> Optional[str]:
        if not raw:
            return None

        suit_alias = {
            "clubs": "clubs",
            "club": "clubs",
            "c": "clubs",
            "diamonds": "diamonds",
            "diamond": "diamonds",
            "d": "diamonds",
            "hearts": "hearts",
            "heart": "hearts",
            "h": "hearts",
            "spades": "spades",
            "spade": "spades",
            "s": "spades",
        }

        key = raw.strip().lower()
        return suit_alias.get(key)

    def _suit_symbol(self, suit_name: str) -> Optional[str]:
        mapping = {
            "clubs": "♣",
            "diamonds": "♦",
            "hearts": "♥",
            "spades": "♠",
        }
        return mapping.get(suit_name)

    def _drawable_suit(self, suit_name: str) -> str:
        return {
            "clubs": "clubs",
            "diamonds": "diamonds",
            "hearts": "hearts",
            "spades": "spades",
        }.get(suit_name, suit_name)
