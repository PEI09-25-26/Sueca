from ultralytics import YOLO
import numpy as np
import os

# -----------------------------
# Função de treino YOLOv8 Classification
# -----------------------------
def train_card_classifier(dataset_path='dataset_split', model_size='n', epochs=100, imgsz=224, batch_size=16, project_name='sueca_cards_classifier'):
    train_dir = os.path.join(dataset_path, 'train')
    val_dir = os.path.join(dataset_path, 'val')

    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        print(f"[ERROR] Pastas de treino/val não encontradas em '{dataset_path}'")
        return

    num_classes = len([d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))])
    print(f"[INFO] Número de classes: {num_classes}")
    print(f"[INFO] Dataset: {os.path.abspath(dataset_path)}")
    print(f"[INFO] Modelo: YOLOv8{model_size}-cls")
    print(f"[INFO] Epochs: {epochs}, Image Size: {imgsz}, Batch Size: {batch_size}")

    response = input("\nIniciar treino? (y/n): ")
    if response.lower() != 'y':
        print("[INFO] Treino cancelado.")
        return

    print("[INFO] Carregando modelo pré-treinado...")
    model = YOLO(f'yolov8{model_size}-cls.pt')

    print("[INFO] A iniciar treino...")
    model.train(
        data=dataset_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        name=project_name,
        patience=20,
        save=True,
        device=0,
        workers=4,
        pretrained=True,
        optimizer='SGD',
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        cos_lr=True,
        augment=True,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.0,
        mixup=0.0,
        copy_paste=0.0,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4
    )

    print("\n[INFO] Treino concluído!")
    print(f"[INFO] Melhor modelo guardado em: runs/classify/{project_name}/weights/best.pt")

    print("\n[INFO] A validar modelo...")
    metrics = model.val()
    print(f"Top-1 Accuracy: {metrics.top1:.4f}")
    print(f"Top-5 Accuracy: {metrics.top5:.4f}")

    print("\n[INFO] Exportando modelo para ONNX...")
    model.export(format='onnx')
    print(f"[INFO] Modelo ONNX guardado em: runs/classify/{project_name}/weights/best.onnx")

if __name__ == "__main__":
    train_card_classifier()