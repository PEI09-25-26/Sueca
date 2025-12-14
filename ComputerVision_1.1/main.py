from camera import Camera
from opencv import CardDetector
from src.utils import display
from yolo import CardClassifier
import cv2
import os
import numpy as np


def main():
    print("Métodos disponíveis: usb, ip, file")
    method = input("Escolha o método de acesso à câmera: ").strip()

    if method == 'usb':
        cameras = Camera.list_usb_cameras()
        print(f"Câmeras USB disponíveis: {cameras}")
        index = int(input("Escolha o índice da câmera: "))
        cam = Camera(method='usb', index=index)
    elif method == 'ip':
        url = input("Digite a URL do stream IP (ex: https://192.168.1.67:8080): ").strip()
        # Adicionar /video ao URL se não estiver presente
        if not url.endswith('/video'):
            url = url.rstrip('/') + '/video'
        print(f"Conectando a: {url}")
        cam = Camera(method='ip', url=url)
    elif method == 'file':
        video_file = input("Digite o caminho do arquivo de vídeo: ")
        cam = Camera(method='file', video_file=video_file)
    else:
        print("Método inválido.")
        return

    cam.open()
    
    # Usar CardDetector (estratégia do projCV - apenas detecção)
    detector = CardDetector(debug=True, min_area=10000)

    # Procura pelo modelo YOLO (para classificação opcional)
    model_path = "runs/classify/sueca_cards_classifier/weights/best.pt"

    classifier = CardClassifier(model_path=model_path)
    last_labels = {}

    print("Iniciando captura de vídeo. Pressione 'q' para sair.")

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            print("Frame não capturado.")
            break

        # Detecção de cartas usando estratégia do projCV
        flatten_cards, img_result, four_corners_set = detector.detect_cards_from_frame(frame)

        # Mostrar feed da câmera com detecções desenhadas
        cv2.imshow("Camera Feed", img_result)

        # Classificar cartas (sem mostrar janelas individuais)
        if flatten_cards and classifier:
            for i, flat_card in enumerate(flatten_cards):
                class_label, conf = classifier.classify(flat_card)
                label_str = f"{class_label} ({conf:.2f})" if class_label else "Unknown"
                
                prev_label = last_labels.get(i)
                if prev_label != label_str:
                    print(f"[INFO] Card {i}: {label_str}")
                    last_labels[i] = label_str

        # Fechar janelas de cartas que desapareceram
        current_indices = set(range(len(flatten_cards)))
        for idx in list(last_labels):
            if idx not in current_indices:
                del last_labels[idx]

        # Stack de cartas detectadas (otimizado)
        if flatten_cards:
            # Apenas criar stack se houver 4 ou menos cartas (evitar lag)
            if len(flatten_cards) <= 4:
                stacked = display.stack_images(0.5, flatten_cards)
                cv2.imshow("Cards Stacked", stacked)
            else:
                # Mostrar apenas contador
                cv2.putText(img_result, f"{len(flatten_cards)} cards detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
