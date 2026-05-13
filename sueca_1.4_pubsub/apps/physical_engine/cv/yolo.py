from ultralytics import YOLO
import torch
import os

class CardClassifier:
    def __init__(self, model_path):
        requested_device = os.getenv("SUECA_YOLO_DEVICE", "auto").strip().lower()
        self.min_confidence = float(os.getenv("SUECA_YOLO_MIN_CONFIDENCE", "0.90"))
        if requested_device in {"", "auto"}:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        elif requested_device.startswith("cuda") and not torch.cuda.is_available():
            print("[Classifier] CUDA requested but not available. Falling back to CPU.")
            device = "cpu"
        else:
            device = requested_device

        print(f"[Classifier] torch.cuda.is_available()={torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[Classifier] GPU: {torch.cuda.get_device_name(0)}")
        print(f"[Classifier] Carregando modelo YOLO em {device}... (min_confidence={self.min_confidence:.2f})")

        self.device = device
        self.model = YOLO(model_path)
        self.model.to(self.device)
        
        # Warm-up
        dummy = torch.zeros((1, 3, 224, 224)).to(self.device)
        print("[Classifier] Executando warm-up...")
        _ = self.model(dummy)
        print("[Classifier] Modelo pronto!")

    def classify(self, image):
        # image = numpy array (H,W,3), shape ~224x224
        results = self.model(image, imgsz=224, verbose=False, device=self.device)
        # Extrair label e confiança
        if results and len(results) > 0:
            class_label = results[0].names[results[0].probs.top1]
            conf = results[0].probs.top1conf.item()
            if conf >= self.min_confidence:
                return class_label, conf
        return None, 0.0