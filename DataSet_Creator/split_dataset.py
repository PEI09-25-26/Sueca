"""
Dataset Splitter for YOLOv8 Classification Training

This script splits the captured card images into train/val sets
required by YOLOv8 classification models.

Usage:
    python split_dataset.py

Directory structure created:
    dataset_split/
    ├── train/
    │   ├── class1/
    │   ├── class2/
    │   └── ...
    └── val/
        ├── class1/
        ├── class2/
        └── ...
"""

import os
import shutil
from pathlib import Path
import random


def split_dataset(source_dir='dataset', dest_dir='dataset_split', train_ratio=0.8, seed=42):
    """
    Split dataset into train and validation sets for YOLOv8 classification.
    
    Args:
        source_dir: Source directory with class subfolders
        dest_dir: Destination directory for train/val split
        train_ratio: Ratio of images to use for training (0.0 to 1.0)
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"[ERROR] Source directory '{source_dir}' not found!")
        return
    
    train_path = Path(dest_dir) / 'train'
    val_path = Path(dest_dir) / 'val'
    
    # Create destination directories
    train_path.mkdir(parents=True, exist_ok=True)
    val_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Splitting dataset from '{source_dir}' to '{dest_dir}'")
    print(f"[INFO] Train ratio: {train_ratio:.0%}, Val ratio: {1-train_ratio:.0%}")
    print("="*60)
    
    total_train = 0
    total_val = 0
    
    # Process each class folder
    for class_dir in sorted(source_path.iterdir()):
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        print(f"\n[CLASS] {class_name}")
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        images = [f for f in class_dir.iterdir() 
                 if f.suffix.lower() in image_extensions]
        
        if not images:
            print(f"  [WARNING] No images found in {class_name}")
            continue
        
        # Shuffle images
        random.shuffle(images)
        
        # Calculate split point
        num_train = int(len(images) * train_ratio)
        train_images = images[:num_train]
        val_images = images[num_train:]
        
        # Create class directories in train and val
        train_class_dir = train_path / class_name
        val_class_dir = val_path / class_name
        train_class_dir.mkdir(exist_ok=True)
        val_class_dir.mkdir(exist_ok=True)
        
        # Copy train images
        for img in train_images:
            shutil.copy2(img, train_class_dir / img.name)
        
        # Copy val images
        for img in val_images:
            shutil.copy2(img, val_class_dir / img.name)
        
        total_train += len(train_images)
        total_val += len(val_images)
        
        print(f"  Total: {len(images)} images")
        print(f"  Train: {len(train_images)} images")
        print(f"  Val:   {len(val_images)} images")
    
    print("\n" + "="*60)
    print(f"[SUMMARY]")
    print(f"  Total train images: {total_train}")
    print(f"  Total val images:   {total_val}")
    print(f"  Total images:       {total_train + total_val}")
    print(f"\n[INFO] Dataset split complete!")
    print(f"[INFO] Train set: {train_path.absolute()}")
    print(f"[INFO] Val set:   {val_path.absolute()}")
    print("\n[NEXT STEPS]")
    print("  1. Train YOLOv8 classification model:")
    print("     from ultralytics import YOLO")
    print("     model = YOLO('yolov8n-cls.pt')")
    print(f"     model.train(data='{dest_dir}', epochs=100)")


if __name__ == "__main__":
    # Configuration
    SOURCE_DIR = 'dataset'
    DEST_DIR = 'dataset_split'
    TRAIN_RATIO = 0.8  # 80% train, 20% val
    RANDOM_SEED = 42
    
    print("YOLOv8 Classification Dataset Splitter")
    print("="*60)
    
    # Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"[ERROR] Directory '{SOURCE_DIR}' not found!")
        print("[INFO] Please run main.py first to capture images.")
    else:
        # Count classes and images
        num_classes = len([d for d in os.listdir(SOURCE_DIR) 
                          if os.path.isdir(os.path.join(SOURCE_DIR, d))])
        print(f"[INFO] Found {num_classes} classes in '{SOURCE_DIR}'")
        
        # Ask for confirmation
        response = input(f"\nSplit dataset with {TRAIN_RATIO:.0%}/{1-TRAIN_RATIO:.0%} train/val ratio? (y/n): ")
        
        if response.lower() == 'y':
            split_dataset(
                source_dir=SOURCE_DIR,
                dest_dir=DEST_DIR,
                train_ratio=TRAIN_RATIO,
                seed=RANDOM_SEED
            )
        else:
            print("[INFO] Operation cancelled.")
