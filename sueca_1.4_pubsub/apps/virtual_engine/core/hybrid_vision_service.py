"""Hybrid vision client that forwards frames to ComputerVision 1.2."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import os
from typing import Optional
import requests
import websockets
import logging
from ..card_mapper import CardMapper

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
        self.cv_url = os.getenv("CV_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.cv_ws_url = os.getenv("CV_SERVICE_WS_URL", "ws://127.0.0.1:8001").rstrip("/")
        self.timeout_s = max(0.5, float(timeout_s))

    def _ensure_started(self, game_id: str) -> None:
        try:
            requests.post(f"{self.cv_url}/cv/start", json={"game_id": game_id}, timeout=2)
        except Exception as e:
            logger.warning(f"Failed to start CV service for game {game_id}: {e}")

    async def recognize_once(self, game_id: str, frame_base64: str, reset_before: bool = True) -> Optional[RecognizedCard]:
        self._ensure_started(game_id)
        ws_url = f"{self.cv_ws_url}/cv/stream/{game_id}"

        logger.info(f"Forwarding frame to CV service at {ws_url} (game: {game_id})")
        try:
            async with websockets.connect(ws_url, open_timeout=self.timeout_s) as ws:
                if reset_before:
                    await ws.send(json.dumps({"action": "reset_cards", "delay": 0, "full": False}))

                await ws.send(frame_base64)

                deadline = asyncio.get_event_loop().time() + self.timeout_s
                while True:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        logger.warning(f"Timeout waiting for detection from CV service (game: {game_id})")
                        return None

                    message = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    data = json.loads(message)
                    detection = data.get("detection")
                    if detection:
                        recognized = self._build_from_detection(detection)
                        if recognized:
                            logger.info(f"Detected card: {recognized.display} (game: {game_id})")
                        return recognized
        except Exception as e:
            logger.error(f"Error in recognize_once for game {game_id}: {e}")
            return None

    async def reset_cv_history(self, game_id: str) -> None:
        """Reset the CV service history (sent_labels) for a clean start of the playing phase."""
        ws_url = f"{self.cv_ws_url}/cv/stream/{game_id}"
        try:
            async with websockets.connect(ws_url, open_timeout=self.timeout_s) as ws:
                await ws.send(json.dumps({"action": "reset_cards", "delay": 0, "full": True}))
                logger.info(f"CV history (sent_labels) reset for game {game_id}")
        except Exception as e:
            logger.error(f"Failed to reset CV history for game {game_id}: {e}")

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
