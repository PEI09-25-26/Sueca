from camera import Camera
from opencv import CardDetector
from src.utils import display
import cv2
import os
import numpy as np
from datetime import datetime


def create_dataset_folder(base_path="dataset"):
    """Create folder structure for dataset"""
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        print(f"[INFO] Created dataset folder: {base_path}")
    return base_path


def get_next_image_number(folder_path):
    """Get the next available image number in a folder"""
    if not os.path.exists(folder_path):
        return 0
    existing_files = [f for f in os.listdir(folder_path) if f.endswith(('.jpg', '.png'))]
    if not existing_files:
        return 0
    # Extract numbers from filenames
    numbers = []
    for f in existing_files:
        try:
            num = int(f.split('_')[1].split('.')[0])
            numbers.append(num)
        except:
            pass
    return max(numbers) + 1 if numbers else 0


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
    
    # Create dataset folder
    dataset_path = create_dataset_folder("dataset")
    
    # Ask for class/category name (optional)
    class_name = input("Nome da classe/categoria (deixe em branco para usar 'cards'): ").strip()
    if not class_name:
        class_name = "cards"
    
    # Create subfolder for this class
    class_folder = os.path.join(dataset_path, class_name)
    if not os.path.exists(class_folder):
        os.makedirs(class_folder)
        print(f"[INFO] Created class folder: {class_folder}")
    
    # Get starting image number
    img_counter = get_next_image_number(class_folder)
    
    # Usar CardDetector (estratégia do projCV - apenas detecção)
    detector = CardDetector(debug=True, min_area=10000)
    
    print("\n" + "="*60)
    print("CONTROLES:")
    print("  's' - Salvar cartas detectadas")
    print("  'c' - Trocar de classe/categoria")
    print("  'q' - Sair")
    print("="*60 + "\n")

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            print("Frame não capturado.")
            break

        # Detecção de cartas usando estratégia do projCV
        flatten_cards, img_result, four_corners_set = detector.detect_cards_from_frame(frame)

        # Add info overlay on camera feed
        info_text = f"Classe: {class_name} | Imagens salvas: {img_counter}"
        cv2.putText(img_result, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(img_result, f"Cartas detectadas: {len(flatten_cards)}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Mostrar feed da câmera com detecções desenhadas
        cv2.imshow("Camera Feed", img_result)

        # Stack de cartas detectadas (otimizado)
        if flatten_cards:
            # Apenas criar stack se houver 4 ou menos cartas (evitar lag)
            if len(flatten_cards) <= 4:
                stacked = display.stack_images(0.5, flatten_cards)
                cv2.imshow("Cards Stacked", stacked)
            else:
                # Mostrar apenas contador
                cv2.putText(img_result, f"{len(flatten_cards)} cards detected", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        key = cv2.waitKey(1) & 0xFF
        
        # Save detected cards
        if key == ord('s') and flatten_cards:
            for i, flat_card in enumerate(flatten_cards):
                filename = f"card_{img_counter:04d}.jpg"
                filepath = os.path.join(class_folder, filename)
                cv2.imwrite(filepath, flat_card)
                print(f"[SAVED] {filepath}")
                img_counter += 1
            print(f"[INFO] Salvou {len(flatten_cards)} carta(s). Total: {img_counter}")
        
        # Change class/category
        elif key == ord('c'):
            new_class = input("\nNovo nome da classe: ").strip()
            if new_class:
                class_name = new_class
                class_folder = os.path.join(dataset_path, class_name)
                if not os.path.exists(class_folder):
                    os.makedirs(class_folder)
                    print(f"[INFO] Created class folder: {class_folder}")
                img_counter = get_next_image_number(class_folder)
                print(f"[INFO] Mudou para classe '{class_name}' (contador: {img_counter})")
        
        # Quit
        elif key == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    print(f"\n[INFO] Total de imagens capturadas: {img_counter}")
    print(f"[INFO] Dataset salvo em: {os.path.abspath(dataset_path)}")


if __name__ == "__main__":
    main()
