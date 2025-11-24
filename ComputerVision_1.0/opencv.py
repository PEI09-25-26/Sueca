import cv2
import numpy as np

class CardCropper:
    def __init__(self, debug=False):
        self.debug = debug

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
            if area > 2000:  # Minimum area threshold for a card, adjust as needed
                # Approximate the contour
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

                # Card contours should have 4 edges
                if len(approx) == 4:
                    # Get bounding rect for cropping
                    x, y, w, h = cv2.boundingRect(approx)
                    img_crop = frame[y:y+h, x:x+w].copy()
                    cropped_cards.append((img_crop, frame))

                    if self.debug:
                        cv2.drawContours(frame, [approx], -1, (0, 255, 0), 3)
        
        return cropped_cards
