from typing import Dict, List, Optional

from ultralytics import YOLO
import torch


class CornerYoloDetector:
    def __init__(
        self,
        model_path: str,
        min_conf: float = 0.80,
        iou: float = 0.5,
        imgsz: int = 640,
        max_det: int = 10,
    ) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[CV2] Loading YOLO model on {device}: {model_path}")
        self.model = YOLO(model_path)
        self.model.to(device)

        self.min_conf = min_conf
        self.iou = iou
        self.imgsz = imgsz
        self.max_det = max_det

    def detect(self, frame_bgr) -> List[Dict]:
        results = self.model.predict(
            source=frame_bgr,
            conf=self.min_conf,
            iou=self.iou,
            imgsz=self.imgsz,
            max_det=self.max_det,
            verbose=False,
        )

        detections: List[Dict] = []
        if not results:
            return detections

        res = results[0]
        boxes = res.boxes
        if boxes is None:
            return detections

        for i in range(len(boxes)):
            box = boxes[i]
            cls_idx = int(box.cls.item())
            conf = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            label = res.names.get(cls_idx, str(cls_idx))

            detections.append(
                {
                    "label": label,
                    "confidence": conf,
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                }
            )

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections


class CardClassifier:
    def __init__(self, model_path: str, imgsz: int = 224) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[CV2-Fallback] Loading classifier model on {device}: {model_path}")
        self.model = YOLO(model_path)
        self.model.to(device)
        self.imgsz = imgsz

    def classify(self, image_bgr) -> tuple[Optional[str], float]:
        results = self.model.predict(source=image_bgr, imgsz=self.imgsz, verbose=False)
        if not results:
            return None, 0.0

        probs = getattr(results[0], "probs", None)
        if probs is None:
            return None, 0.0

        top1 = getattr(probs, "top1", None)
        top1_conf = getattr(probs, "top1conf", None)
        if top1 is None or top1_conf is None:
            return None, 0.0

        label = results[0].names.get(int(top1), str(top1))
        confidence = float(top1_conf.item())
        return label, confidence
