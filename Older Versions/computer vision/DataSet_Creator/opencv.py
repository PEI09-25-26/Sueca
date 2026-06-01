import cv2
import numpy as np
from src.utils.DistanceHelper import DistanceHelper


class CardDetector:
    """Detector de cartas baseado na estratégia do projCV - foca apenas na detecção de cartas na mesa"""
    
    def __init__(self, debug=True, min_area=10000, max_cards=10):
        self.debug = debug
        self.min_area = min_area  # Área mínima para considerar um contorno como carta
        self.max_cards = max_cards  # Limitar número máximo de cartas a processar
        self.standard_width = 200
        self.standard_height = 300

    def get_thresh(self, img):
        """Preprocessa a imagem para detecção de bordas"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        canny = cv2.Canny(blur, 42, 89)
        kernel = np.ones((2, 2))
        dial = cv2.dilate(canny, kernel=kernel, iterations=2)
        return dial

    def find_corners_set(self, img, original, draw=False):
        """Encontra os cantos de contornos retangulares (cartas) na imagem"""
        contours, hier = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Processar apenas os maiores contornos (otimização)
        proper = sorted(contours, key=cv2.contourArea, reverse=True)[:self.max_cards * 2]
        four_corners_set = []

        for cnt in proper:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, closed=True)

            if area > self.min_area:
                approx = cv2.approxPolyDP(cnt, 0.01 * perimeter, closed=True)
                num_corners = len(approx)

                if num_corners == 4:
                    x, y, w, h = cv2.boundingRect(approx)

                    if draw:
                        cv2.rectangle(original, (x, y), (x + w, y + h), (0, 255, 0), 3)

                    # Ordenar os cantos: top left, bot left, bot right, top right
                    l1 = np.array(approx[0]).tolist()
                    l2 = np.array(approx[1]).tolist()
                    l3 = np.array(approx[2]).tolist()
                    l4 = np.array(approx[3]).tolist()

                    finalOrder = []
                    sortedX = sorted([l1, l2, l3, l4], key=lambda x: x[0][0])

                    # Metade esquerda
                    finalOrder.extend(sorted(sortedX[0:2], key=lambda x: x[0][1]))

                    # Metade direita (maior y primeiro)
                    finalOrder.extend(sorted(sortedX[2:4], key=lambda x: x[0][1], reverse=True))

                    four_corners_set.append(finalOrder)

                    if draw:
                        for a in approx:
                            cv2.circle(original, (a[0][0], a[0][1]), 6, (255, 0, 0), 3)

        return four_corners_set

    def find_flatten_cards(self, img, set_of_corners, debug=False):
        """Aplica transformação de perspectiva para achatar/normalizar as cartas"""
        img_outputs = []

        for i, corners in enumerate(set_of_corners):
            top_left = corners[0][0]
            bottom_left = corners[1][0]
            bottom_right = corners[2][0]
            top_right = corners[3][0]

            widthA = DistanceHelper.euclidean(bottom_right[0], bottom_right[1], bottom_left[0], bottom_left[1])
            widthB = DistanceHelper.euclidean(top_right[0], top_right[1], top_left[0], top_left[1])
            heightA = DistanceHelper.euclidean(top_right[0], top_right[1], bottom_right[0], bottom_right[1])
            heightB = DistanceHelper.euclidean(top_left[0], top_left[1], bottom_left[0], bottom_left[1])

            maxWidth = int(max(widthA, widthB))
            maxHeight = int(max(heightA, heightB))

            # Determinar orientação
            if maxWidth > maxHeight:
                dst_width, dst_height = self.standard_height, self.standard_width
                rotate90 = True
            else:
                dst_width, dst_height = self.standard_width, self.standard_height
                rotate90 = False

            pts1 = np.float32([top_left, bottom_left, bottom_right, top_right])
            pts2 = np.float32([[0, 0], [0, dst_height], [dst_width, dst_height], [dst_width, 0]])

            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            img_output = cv2.warpPerspective(img, matrix, (dst_width, dst_height))

            # Rodar 90º se necessário
            if rotate90:
                img_output = cv2.rotate(img_output, cv2.ROTATE_90_CLOCKWISE)

            img_outputs.append(img_output)

        return img_outputs

    def detect_cards_from_frame(self, frame):
        """Método principal para detectar cartas num frame"""
        # Reduzir resolução para melhor performance
        scale = 0.75
        height, width = frame.shape[:2]
        small_frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
        
        img_result = small_frame.copy() if self.debug else small_frame
        img_result2 = small_frame.copy()

        # 1. Preprocessamento
        thresh = self.get_thresh(small_frame)

        # 2. Encontrar cantos das cartas
        four_corners_set = self.find_corners_set(thresh, img_result, draw=self.debug)

        # 3. Achatar cartas (limitar ao max_cards)
        flatten_cards = self.find_flatten_cards(img_result2, four_corners_set[:self.max_cards], debug=False)

        # Retornar cartas achatadas e frame com desenhos (se debug ativo)
        # Redimensionar img_result de volta ao tamanho original se necessário
        if self.debug:
            img_result = cv2.resize(img_result, (width, height))
        
        return flatten_cards, img_result, four_corners_set