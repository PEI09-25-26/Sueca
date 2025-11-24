from camera import Camera
from opencv import CardCropper
from src.utils import display
from yolo import CardClassifier
import cv2
import os

def main():
    print("Métodos disponíveis: usb, ip, file")
    method = input("Escolha o método de acesso à câmera: ").strip()

    if method == 'usb':
        cameras = Camera.list_usb_cameras()
        print(f"Câmeras USB disponíveis: {cameras}")
        index = int(input("Escolha o índice da câmera: "))
        cam = Camera(method='usb', index=index)
    elif method == 'ip':
        url = input("Digite a URL do stream IP: ")
        cam = Camera(method='ip', url=url)
    elif method == 'file':
        video_file = input("Digite o caminho do arquivo de vídeo: ")
        cam = Camera(method='file', video_file=video_file)
    else:
        print("Método inválido.")
        return

    cam.open()
    cropper = CardCropper(debug=True)

    # Procura pelo modelo mais recente na pasta runs/detect/
    runs_path = "./runs/detect/"
    if os.path.exists(runs_path):
        train_folders = [f for f in os.listdir(runs_path) if f.startswith('train')]
        if train_folders:
            latest_train = sorted(train_folders, key=lambda x: int(x.replace('train', '') or '0'))[-1]
            model_path = os.path.join(runs_path, latest_train, 'weights', 'best.pt')
        else:
            print("Nenhum modelo treinado encontrado na pasta runs/detect/")
            return
    else:
        print("Nenhum modelo treinado encontrado na pasta runs/detect/")
        return

    classifier = CardClassifier(model_path=model_path)
    last_labels = {}  # Dictionary to keep track of last known classification per card index

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            print("Frame não capturado.")
            break

        cropped_cards = cropper.crop_cards_from_frame(frame)

        # Show the camera feed
        cv2.imshow("Camera Feed", frame)

        # Make a set of indices for cards just in case quantity changes dynamically
        current_indices = set()
        for i, (img_crop, original) in enumerate(cropped_cards):
            class_label, conf = classifier.classify(img_crop)
            label_str = f"{class_label} ({conf:.2f})" if class_label else "Unknown"
            current_indices.add(i)
            # Compare with previous label
            prev_label = last_labels.get(i)
            if prev_label != label_str:
                print(f"[INFO] Card {i}: Classification changed from {prev_label} to {label_str}")
                last_labels[i] = label_str  # Update record
            cv2.putText(img_crop, label_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255,0,0), 2, cv2.LINE_AA)
            cv2.imshow(f"Card_{i}", img_crop)  # Use a constant window name per index
        
        # Close windows of any cards that have "disappeared"
        for idx in list(last_labels):
            if idx not in current_indices:
                cv2.destroyWindow(f"Card_{idx}")
                del last_labels[idx]

        if cropped_cards:
            images = [img_crop for img_crop, _ in cropped_cards]
            stacked = display.stack_images(0.5, images)
            cv2.imshow("Cards Stacked", stacked)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
