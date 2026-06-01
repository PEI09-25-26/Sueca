"""
Hybrid vision service for incremental card recognition.

Design goals:
- Keep API simple for a fast-moving project.
- Be resilient: if detection is noisy, require a short streak before confirming.
- Share progress by game_id so host and virtual player stay in sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple
import base64


@dataclass
class RecognizedCard:
    card_id: int
    rank: str
    suit_symbol: str
    suit_name: str
    drawable_key: str
    display: str


@dataclass
class HybridSessionState:
    game_id: str
    target_count: int = 10
    cards: List[RecognizedCard] = field(default_factory=list)
    last_candidate_key: Optional[str] = None
    streak: int = 0


class HybridVisionService:
    """Stateful recognizer used by /api/hybrid/* routes."""

    SUIT_NAME_TO_SYMBOL = {
        "clubs": "♣",
        "diamonds": "♦",
        "hearts": "♥",
        "spades": "♠",
    }

    SUIT_NAME_TO_DRAWABLE = {
        "clubs": "clubs",
        "diamonds": "diamonds",
        "hearts": "hearts",
        "spades": "spades",
    }

    def __init__(
        self,
        templates_root: Optional[Path] = None,
        confirm_streak: int = 3,
        cv12_root: Optional[Path] = None,
    ) -> None:
        self.templates_root = templates_root
        self.cv12_root = cv12_root or (Path(__file__).resolve().parent.parent / "ComputerVision_1.2")
        self.confirm_streak = confirm_streak
        self._lock = Lock()
        self._sessions: Dict[str, HybridSessionState] = {}

        self._cv12_corner_detector = None
        self._cv12_classifier = None
        self._init_cv12_pipeline()

        if templates_root is not None:
            self._rank_templates = self._load_templates(templates_root / "ranks")
            self._suit_templates = self._load_templates(templates_root / "suits")
        else:
            self._rank_templates = {}
            self._suit_templates = {}

    def reset_session(self, game_id: str, target_count: int = 10) -> HybridSessionState:
        with self._lock:
            session = HybridSessionState(game_id=game_id, target_count=max(1, int(target_count)))
            self._sessions[game_id] = session
            return session

    def get_session(self, game_id: str, target_count: int = 10) -> HybridSessionState:
        with self._lock:
            session = self._sessions.get(game_id)
            if session is None:
                session = HybridSessionState(game_id=game_id, target_count=max(1, int(target_count)))
                self._sessions[game_id] = session
            return session

    def get_status_payload(self, game_id: str, target_count: int = 10) -> dict:
        session = self.get_session(game_id, target_count)
        return {
            "success": True,
            "game_id": game_id,
            "confirmed_count": len(session.cards),
            "target_count": session.target_count,
            "done": len(session.cards) >= session.target_count,
            "cards": [self._card_to_payload(c) for c in session.cards],
        }

    def process_frame(self, game_id: str, frame_base64: str, target_count: int = 10) -> dict:
        session = self.get_session(game_id, target_count)

        if len(session.cards) >= session.target_count:
            return {
                "success": True,
                "recognized": False,
                "confirmed": False,
                "message": "Session already complete",
                **self.get_status_payload(game_id, target_count),
            }

        decoded = self._decode_base64_image(frame_base64)
        if decoded is None:
            return {
                "success": False,
                "recognized": False,
                "confirmed": False,
                "message": "Invalid frame_base64",
                **self.get_status_payload(game_id, target_count),
            }

        card_candidate = self._recognize_card(decoded)
        if card_candidate is None:
            self._reset_streak(session)
            return {
                "success": True,
                "recognized": False,
                "confirmed": False,
                "message": "No valid card detected",
                **self.get_status_payload(game_id, target_count),
            }

        candidate_key = f"{card_candidate.rank}{card_candidate.suit_symbol}"
        self._update_streak(session, candidate_key)

        confirmed = False
        if session.streak >= self.confirm_streak:
            if not any(c.card_id == card_candidate.card_id for c in session.cards):
                session.cards.append(card_candidate)
                confirmed = True
            self._reset_streak(session)

        return {
            "success": True,
            "recognized": True,
            "confirmed": confirmed,
            "message": "Card confirmed" if confirmed else "Candidate recognized",
            "card": self._card_to_payload(card_candidate),
            "streak": session.streak,
            "required_streak": self.confirm_streak,
            **self.get_status_payload(game_id, target_count),
        }

    def recognize_once(self, frame_base64: str) -> Optional[RecognizedCard]:
        """Recognize a single frame without touching session state."""
        decoded = self._decode_base64_image(frame_base64)
        if decoded is None:
            return None
        return self._recognize_card(decoded)

    def _update_streak(self, session: HybridSessionState, candidate_key: str) -> None:
        if session.last_candidate_key == candidate_key:
            session.streak += 1
        else:
            session.last_candidate_key = candidate_key
            session.streak = 1

    def _reset_streak(self, session: HybridSessionState) -> None:
        session.last_candidate_key = None
        session.streak = 0

    def _card_to_payload(self, card: RecognizedCard) -> dict:
        return {
            "id": card.card_id,
            "rank": card.rank,
            "suit_symbol": card.suit_symbol,
            "suit": card.suit_name,
            "drawable_key": card.drawable_key,
            "display": card.display,
        }

    def _decode_base64_image(self, frame_base64: str):
        try:
            import numpy as np
            import cv2

            raw = base64.b64decode(frame_base64)
            arr = np.frombuffer(raw, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def _recognize_card(self, image_bgr) -> Optional[RecognizedCard]:
        # YOLO-only recognition path from ComputerVision_1.2.
        return self._recognize_with_cv12(image_bgr)

    def _init_cv12_pipeline(self) -> None:
        import os

        if not self.cv12_root.exists():
            return

        yolo_path = self.cv12_root / "yolo.py"
        if not yolo_path.exists():
            return

        try:
            yolo_mod = self._import_module_from_file("cv12_yolo", yolo_path)
        except Exception:
            return

        corner_detector_cls = getattr(yolo_mod, "CornerYoloDetector", None)
        classifier_cls = getattr(yolo_mod, "CardClassifier", None)
        if corner_detector_cls is None:
            return

        corner_model_path = self._resolve_cv12_corner_model_path()
        if not corner_model_path:
            return

        min_conf = float(os.getenv("CV2_DETECT_MIN_CONF", "0.45"))
        try:
            self._cv12_corner_detector = corner_detector_cls(model_path=corner_model_path, min_conf=min_conf)
        except Exception:
            self._cv12_corner_detector = None

        classifier_path = self._resolve_cv12_classifier_model_path()
        if classifier_cls is not None and classifier_path:
            try:
                self._cv12_classifier = classifier_cls(model_path=classifier_path)
            except Exception:
                self._cv12_classifier = None

    def _import_module_from_file(self, module_name: str, file_path: Path):
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _resolve_cv12_corner_model_path(self) -> Optional[str]:
        import os

        env_path = os.getenv("CV2_MODEL_PATH")
        candidates: List[Path] = []
        if env_path:
            candidates.append(Path(env_path))

        candidates.extend(
            [
                self.cv12_root / "runs" / "archive3_final" / "weights" / "best.pt",
                self.cv12_root / "runs" / "detect" / "corner_cards" / "weights" / "best.pt",
                self.cv12_root / "runs" / "detect" / "train" / "weights" / "best.pt",
                self.cv12_root / "best.pt",
            ]
        )

        for path in candidates:
            if path.exists() and path.is_file():
                return str(path)
        return None

    def _resolve_cv12_classifier_model_path(self) -> Optional[str]:
        import os

        env_path = os.getenv("CV2_CLASSIFIER_MODEL_PATH")
        candidates: List[Path] = []
        if env_path:
            candidates.append(Path(env_path))

        candidates.extend(
            [
                self.cv12_root / "runs" / "classify" / "sueca_cards_classifier" / "weights" / "best.pt",
                Path(__file__).resolve().parent.parent / "DataSet_Creator" / "runs" / "classify" / "sueca_cards_classifier" / "weights" / "best.pt",
                self.cv12_root / "yolov8n-cls.pt",
            ]
        )

        for path in candidates:
            if path.exists() and path.is_file():
                return str(path)
        return None

    def _recognize_with_cv12(self, image_bgr) -> Optional[RecognizedCard]:
        candidates: List[Tuple[str, float]] = []

        if self._cv12_corner_detector is not None:
            try:
                detections = self._cv12_corner_detector.detect(image_bgr)
                if detections:
                    top = detections[0]
                    print(
                        f"[HYBRID-CV] detector top label={top.get('label')} conf={float(top.get('confidence', 0.0)):.3f}"
                    )
                for det in detections:
                    label = str(det.get("label", "")).strip()
                    conf = float(det.get("confidence", 0.0))
                    if self._is_label_card_like(label):
                        candidates.append((label, conf))
            except Exception:
                pass

        # Still YOLO-only: classifier fallback over full frame when detector labels are not card IDs.
        if not candidates and self._cv12_classifier is not None:
            try:
                label, conf = self._cv12_classifier.classify(image_bgr)
                print(f"[HYBRID-CV] classifier label={label} conf={float(conf):.3f}")
                if label and self._is_label_card_like(label):
                    candidates.append((label, float(conf)))
            except Exception:
                pass

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[1], reverse=True)
        best_label = candidates[0][0]
        rank, suit_key = self._parse_cv12_label(best_label)
        if rank is None or suit_key is None:
            return None

        return self._build_recognized_card(rank, suit_key)

    def _is_label_card_like(self, label: str) -> bool:
        rank, suit = self._parse_cv12_label(label)
        return rank is not None and suit is not None

    def _parse_cv12_label(self, label: str):
        clean = label.strip()
        if len(clean) < 2:
            return None, None

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
        suit_alias = {
            "c": "clubs",
            "club": "clubs",
            "clubs": "clubs",
            "d": "diamonds",
            "diamond": "diamonds",
            "diamonds": "diamonds",
            "h": "hearts",
            "heart": "hearts",
            "hearts": "hearts",
            "s": "spades",
            "spade": "spades",
            "spades": "spades",
        }

        raw = clean.lower().replace(" ", "")

        # Compact formats like "as", "10h", "qc".
        if len(raw) >= 2 and raw[-1] in suit_alias:
            compact_rank = rank_alias.get(raw[:-1])
            compact_suit = suit_alias.get(raw[-1])
            if compact_rank and compact_suit:
                return compact_rank, compact_suit

        normalized = raw.replace("of", "_").replace("-", "_")
        tokens = [t for t in normalized.split("_") if t]
        rank = None
        suit = None
        for token in tokens:
            if rank is None and token in rank_alias:
                rank = rank_alias[token]
                continue
            if suit is None and token in suit_alias:
                suit = suit_alias[token]

        if rank and suit:
            return rank, suit

        return None, None

    def _build_recognized_card(self, rank: str, suit_key: str) -> Optional[RecognizedCard]:
        rank = rank.upper()
        suit_key = suit_key.lower()

        if suit_key not in self.SUIT_NAME_TO_SYMBOL:
            return None

        from card_mapper import CardMapper

        if rank not in CardMapper.RANKS:
            return None

        suit_symbol = self.SUIT_NAME_TO_SYMBOL[suit_key]
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

        drawable_key = f"{self.SUIT_NAME_TO_DRAWABLE[suit_key]}_{drawable_rank}"

        return RecognizedCard(
            card_id=card_id,
            rank=rank,
            suit_symbol=suit_symbol,
            suit_name=suit_key,
            drawable_key=drawable_key,
            display=f"{rank}{suit_symbol}",
        )

    def _extract_largest_card(self, image_bgr, cv2, np):
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 12000:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) != 4:
                continue

            pts = approx.reshape(4, 2).astype("float32")
            rect = self._order_points(pts, np)
            width, height = 200, 300
            dst = np.array(
                [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                dtype="float32",
            )

            matrix = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image_bgr, matrix, (width, height))
            return warped

        return None

    def _order_points(self, pts, np):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def _extract_rank_suit_regions(self, warped, cv2):
        # Corner where rank+suit live in a standard card perspective.
        corner = warped[5:120, 5:55]
        if corner.size == 0:
            return None, None

        corner = cv2.resize(corner, (160, 360), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, bin_img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        parts = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h < 200:
                continue
            crop = bin_img[y:y + h, x:x + w]
            parts.append((y, crop))
            if len(parts) == 2:
                break

        if len(parts) < 2:
            return None, None

        parts.sort(key=lambda item: item[0])
        rank = cv2.resize(parts[0][1], (70, 125), interpolation=cv2.INTER_AREA)
        suit = cv2.resize(parts[1][1], (70, 100), interpolation=cv2.INTER_AREA)
        return rank, suit

    def _best_template_match(self, query_img, templates, cv2, np):
        if not templates:
            return None, 0.0

        best_name = None
        best_score = -1.0

        for name, template in templates.items():
            if template.shape != query_img.shape:
                resized = cv2.resize(template, (query_img.shape[1], query_img.shape[0]))
            else:
                resized = template

            diff = cv2.absdiff(query_img, resized)
            normalized = 1.0 - (float(np.sum(diff)) / float(query_img.size * 255))
            score = max(0.0, min(1.0, normalized))

            if score > best_score:
                best_name = name
                best_score = score

        if best_score < 0.35:
            return None, best_score

        return best_name, best_score

    def _load_templates(self, folder: Path):
        templates = {}
        if not folder.exists():
            return templates

        try:
            import cv2
        except Exception:
            return templates

        for img_path in sorted(folder.glob("*.jpg")):
            image = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            _, bin_img = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            templates[img_path.stem] = bin_img

        return templates
