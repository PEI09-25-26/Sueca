from ultralytics import YOLO
import numpy as np

class CardClassifier:
    def __init__(self, model_path=None):
        print(f"Carregando modelo YOLO de: {model_path}")
        if model_path is None or not model_path:
            # fallback to a default model if not given
            model_path = 'yolov8n.pt'
        self.model = YOLO(model_path)
        # Class names (update if your model/class order is different)
        self.classnames = [
            "as_espadas", "valete_copas","10_espadas"
        ]
    
    def classify(self, img, conf_threshold=0.2):
        # img: cropped card (numpy array)
        results = self.model(img, conf=conf_threshold, verbose=False)
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            # Take the highest confidence detection as card class
            best_box = max(boxes, key=lambda b: b.conf[0] if hasattr(b, "conf") else 0)
            class_id = int(best_box.cls[0])
            confidence = float(best_box.conf[0])
            label = self.classnames[class_id] if class_id < len(self.classnames) else str(class_id)
            return label, confidence
        else:
            return None, 0.0
