from ultralytics import YOLO
import os


def train_card_classifier():
    """Train YOLOv8 classification model for card recognition"""
    
    # Configuration
    DATASET_PATH = 'dataset_split'  # Path to train/val split dataset
    MODEL_SIZE = 'n'  # Options: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
    EPOCHS = 100
    IMAGE_SIZE = 224  # Standard for classification
    BATCH_SIZE = 16  # Adjust based on GPU memory
    PROJECT_NAME = 'sueca_cards_classifier'
    
    # Check if dataset exists
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] Dataset not found at '{DATASET_PATH}'")
        print("[INFO] Please run 'python split_dataset.py' first to create train/val split")
        return
    
    # Check train and val directories
    train_dir = os.path.join(DATASET_PATH, 'train')
    val_dir = os.path.join(DATASET_PATH, 'val')
    
    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        print(f"[ERROR] Missing 'train' or 'val' directory in '{DATASET_PATH}'")
        return
    
    # Count classes
    num_classes = len([d for d in os.listdir(train_dir) 
                      if os.path.isdir(os.path.join(train_dir, d))])
    
    print("="*60)
    print("YOLOv8 Classification Training")
    print("="*60)
    print(f"Dataset path: {os.path.abspath(DATASET_PATH)}")
    print(f"Number of classes: {num_classes}")
    print(f"Model size: YOLOv8{MODEL_SIZE}-cls")
    print(f"Epochs: {EPOCHS}")
    print(f"Image size: {IMAGE_SIZE}x{IMAGE_SIZE}")
    print(f"Batch size: {BATCH_SIZE}")
    print("="*60)
    
    # Confirm training
    response = input("\nStart training? (y/n): ")
    if response.lower() != 'y':
        print("[INFO] Training cancelled.")
        return
    
    print("\n[INFO] Loading model...")
    # Load pre-trained YOLOv8 classification model
    model = YOLO(f'yolov8{MODEL_SIZE}-cls.pt')
    
    print("[INFO] Starting training...")
    # Train the model
    results = model.train(
        data=DATASET_PATH,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        name=PROJECT_NAME,
        patience=20,  # Early stopping patience
        save=True,
        device=0,  # Use GPU 0, set to 'cpu' if no GPU available
        workers=4,
        pretrained=True,
        optimizer='SGD',
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        cos_lr=True,
        augment=True,
        # Data augmentation
        degrees=10.0,  # Rotation
        translate=0.1,  # Translation
        scale=0.5,     # Scale
        shear=0.0,     # Shear
        perspective=0.0,  # Perspective
        flipud=0.0,    # Flip up-down
        fliplr=0.5,    # Flip left-right (50% chance)
        mosaic=0.0,    # Mosaic augmentation (not ideal for classification)
        mixup=0.0,     # Mixup augmentation
        copy_paste=0.0,  # Copy-paste augmentation
        hsv_h=0.015,   # HSV-Hue augmentation
        hsv_s=0.7,     # HSV-Saturation augmentation
        hsv_v=0.4      # HSV-Value augmentation
    )
    
    print("\n[INFO] Training complete!")
    print(f"[INFO] Best model saved at: runs/classify/{PROJECT_NAME}/weights/best.pt")
    
    # Validate the model
    print("\n[INFO] Running validation...")
    metrics = model.val()
    
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    print(f"Top-1 Accuracy: {metrics.top1:.4f}")
    print(f"Top-5 Accuracy: {metrics.top5:.4f}")
    print("="*60)
    
    # Export the model
    print("\n[INFO] Exporting model to ONNX format...")
    model.export(format='onnx')
    print(f"[INFO] ONNX model saved at: runs/classify/{PROJECT_NAME}/weights/best.onnx")
    
    print("\n[SUCCESS] Training pipeline complete!")
    print("\n[NEXT STEPS]")
    print("  1. Test the model:")
    print(f"     from ultralytics import YOLO")
    print(f"     model = YOLO('runs/classify/{PROJECT_NAME}/weights/best.pt')")
    print(f"     results = model.predict('test_image.jpg')")
    print("\n  2. Use the model in your application:")
    print(f"     classifier = CardClassifier(model_path='runs/classify/{PROJECT_NAME}/weights/best.pt')")


if __name__ == "__main__":
    try:
        train_card_classifier()
    except KeyboardInterrupt:
        print("\n[INFO] Training interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Training failed: {e}")
        import traceback
        traceback.print_exc()
