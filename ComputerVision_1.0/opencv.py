import cv2
import numpy as np

class CardCropper:
    def __init__(self, debug=True, min_area=5000, max_area=100000, ratio_tolerance=0.15):
        self.debug = debug
        self.min_area = min_area  # Área mínima para filtrar ruído
        self.max_area = max_area  # Área máxima para evitar objetos grandes
        self.target_ratio = 63 / 88  # 0.716 - proporção de uma carta
        self.ratio_tolerance = ratio_tolerance  # Tolerância na proporção

    def crop_cards_from_frame(self, frame):
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detect edges
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cropped_cards = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # Filtro básico de área (elimina ruído)
            if area < self.min_area:
                continue
            
            # Approximate the contour
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            # Card contours should have 4 edges
            if len(approx) == 4:
                # Get bounding rect
                x, y, w, h = cv2.boundingRect(approx)
                
                # Calcular aspect ratio (proporção largura/altura)
                aspect_ratio = w / h if h > 0 else 0
                
                # Verificar se corresponde à proporção de uma carta (63/88)
                # Pode estar vertical (63/88 ≈ 0.716) ou horizontal (88/63 ≈ 1.397)
                is_vertical = abs(aspect_ratio - self.target_ratio) <= self.ratio_tolerance
                is_horizontal = abs(aspect_ratio - (1 / self.target_ratio)) <= self.ratio_tolerance
                
                if is_vertical or is_horizontal:
                    # É uma carta!
                    img_crop = frame[y:y+h, x:x+w].copy()
                    cropped_cards.append((img_crop, frame))

                    if self.debug:
                        # Verde = carta detetada
                        cv2.drawContours(frame, [approx], -1, (0, 255, 0), 3)
                        # Mostrar ratio para debug
                        cv2.putText(frame, f"R:{aspect_ratio:.2f}", (x, y-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                elif self.debug:
                    # Vermelho = retângulo rejeitado (proporção errada)
                    cv2.drawContours(frame, [approx], -1, (0, 0, 255), 2)
                    cv2.putText(frame, f"R:{aspect_ratio:.2f}", (x, y-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return cropped_cards