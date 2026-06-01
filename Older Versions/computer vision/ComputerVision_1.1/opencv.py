import cv2
import numpy as np

class CardDetector:
    def __init__(self, debug=False, min_area=10000):
        self.debug = debug
        self.min_area = min_area

    def detect_cards_from_frame(self, frame):
        if self.debug:
            print(f"[Detector] Iniciando detecção de cartas. Frame shape: {frame.shape}")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        flatten_cards = []
        img_result = frame.copy()
        four_corners_set = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_area:
                approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    card = frame[y:y+h, x:x+w]
                    flatten_cards.append(card)
                    four_corners_set.append(approx)
                    cv2.drawContours(img_result, [approx], -1, (0, 255, 0), 2)
                    if self.debug:
                        print(f"[Detector] Carta detectada: area={area}, bbox=({x},{y},{w},{h})")

        if self.debug:
            print(f"[Detector] Detecção concluída. Cartas detectadas: {len(flatten_cards)}")

        return flatten_cards, img_result, four_corners_set
