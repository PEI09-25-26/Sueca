import threading
import queue
import cv2
import os
import numpy as np
from camera import Camera
from opencv import CardDetector
from yolo import CardClassifier
from src.utils import display
import time

frame_queue = queue.Queue(maxsize=5)
stop_event = threading.Event()

def capture_loop(cam, frame_queue, stop_event):
    print("[Capture] Thread de captura iniciada.")
    first_frame = True
    while not stop_event.is_set():
        try:
            ret, frame = cam.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            if first_frame:
                print(f"[Capture] Primeiro frame recebido: {frame.shape}")
                first_frame = False
            
            if frame_queue.full():
                try: frame_queue.get_nowait()
                except queue.Empty: pass
            
            try: frame_queue.put(frame, block=False)
            except queue.Full: pass
            
            time.sleep(0.01)
            time.sleep(0.01)  # evita CPU a 100%
        except Exception as e:
            print(f"[Capture] Erro fatal: {e}")
            stop_event.set()
            break

def processing_loop(detector, classifier, frame_queue, stop_event):
    try:
        print("[Processing] Inicializando interface gráfica...")
        print("[Processing] Entrando no loop de processamento...")
        last_labels = {}
        cv2.namedWindow("Camera Feed", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Camera Feed", 1280, 720)
        cv2.namedWindow("Cards Stacked", cv2.WINDOW_NORMAL)
        
        # Mostrar tela inicial para garantir que a janela abre
        blank = np.zeros((720, 1280, 3), np.uint8)
        cv2.putText(blank, "Aguardando frames...", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Camera Feed", blank)
        cv2.waitKey(1)
        print("[Processing] Interface pronta. Entrando no loop...")

        frame_count = 0
        last_log = time.time()

        while not stop_event.is_set():
            if frame_queue.empty():
                if time.time() - last_log > 2.0:
                    print("[Processing] Aguardando frames...")
                    last_log = time.time()
                key = cv2.waitKey(10) & 0xFF
                if key == ord('q'):
                    stop_event.set()
                    break
                continue

            frame = frame_queue.get()
            if frame_count == 0:
                print("[Processing] Recebendo frames no loop principal.")
            frame_count += 1
            flatten_cards, img_result, corners = detector.detect_cards_from_frame(frame)

            if flatten_cards and classifier:
                for i, flat_card in enumerate(flatten_cards):
                    h, w = flat_card.shape[:2]
                    if h < 150 or w < 150 or h > 600 or w > 600:
                        continue
                    try:
                        class_label, conf = classifier.classify(flat_card)
                        label_str = f"{class_label} ({conf:.2f})" if class_label else "Unknown"
                        
                        # Desenhar o nome da carta na tela
                        if i < len(corners):
                            x, y, w, h = cv2.boundingRect(corners[i])
                            cv2.putText(img_result, label_str, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                        prev_label = last_labels.get(i)
                        if prev_label != label_str:
                            print(f"[Classificação] Card {i}: {label_str}")
                            last_labels[i] = label_str
                    except Exception as e:
                        print(f"[ERRO] Classificação falhou: {e}")
                        pass

            cv2.imshow("Camera Feed", img_result)
            if flatten_cards:
                if len(flatten_cards) <= 4:
                    stacked = display.stack_images(0.5, flatten_cards)
                    cv2.imshow("Cards Stacked", stacked)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                stop_event.set()
                break
    except Exception as e:
        print(f"[Processing] Erro fatal: {e}")
    finally:
        cv2.destroyAllWindows()

def main():
    cv2.setNumThreads(1)
    # Escolha da câmera...
    print("Métodos disponíveis: usb, ip, file")
    method = input("Escolha o método de acesso à câmera: ").strip()

    if method == 'usb':
        cameras = Camera.list_usb_cameras()
        print(f"Câmeras USB disponíveis: {cameras}")
        index = int(input("Escolha o índice da câmera: "))
        cam = Camera(method='usb', index=index)
    else:
        print("Só USB implementado neste teste")
        return

    # Inicializar GUI na thread principal ANTES de iniciar threads secundárias
    print("[Main] Inicializando interface gráfica...")
    cv2.namedWindow("Camera Feed", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Camera Feed", 1280, 720)
    cv2.namedWindow("Cards Stacked", cv2.WINDOW_NORMAL)
    
    blank = np.zeros((720, 1280, 3), np.uint8)
    cv2.putText(blank, "Iniciando...", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow("Camera Feed", blank)
    cv2.waitKey(100)
    print("[Main] Interface gráfica pronta.")

    cam.open()
    print(f"Camera opened: {cam}, resolution: {cam.resolution}")

    detector = CardDetector(debug=True, min_area=10000)
    best_pt_path = "/home/goncalo/Desktop/1S_3M/PEI/Sueca/DataSet_Creator/runs/classify/sueca_cards_classifier/weights/best.pt"
    classifier = CardClassifier(model_path=best_pt_path) if os.path.exists(best_pt_path) else None
    cv2.waitKey(1)

    # Criar threads
    t1 = threading.Thread(target=capture_loop, args=(cam, frame_queue, stop_event), daemon=True)
    t1.start()
    processing_loop(detector, classifier, frame_queue, stop_event)

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
