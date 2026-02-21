"""
Script to analyze YOLOv8 card classification model performance.
Calculates precision, recall, and F1-score for each card category.
"""

from ultralytics import YOLO
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from collections import defaultdict

# Configuration
MODEL_PATH = "runs/classify/sueca_cards_classifier/weights/best.pt"
VAL_DATA_PATH = "dataset_split/val"

# Card categories
NUMBERED_CARDS = ['2c', '2d', '2h', '2s', '3c', '3d', '3h', '3s', 
                  '4c', '4d', '4h', '4s', '5c', '5d', '5h', '5s',
                  '6c', '6d', '6h', '6s', '7c', '7d', '7h', '7s']

FACE_CARDS = ['Ac', 'Ad', 'Ah', 'As', 'Jc', 'Jd', 'Jh', 'Js',
              'Qc', 'Qd', 'Qh', 'Qs', 'Kc', 'Kd', 'Kh', 'Ks']


def load_validation_data(val_path):
    """Load all validation images and their true labels."""
    val_path = Path(val_path)
    images = []
    labels = []
    
    for class_dir in sorted(val_path.iterdir()):
        if class_dir.is_dir():
            class_name = class_dir.name
            for img_file in class_dir.glob('*'):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    images.append(str(img_file))
                    labels.append(class_name)
    
    return images, labels


def get_predictions(model, images):
    """Get model predictions for all images."""
    predictions = []
    
    print(f"Running predictions on {len(images)} images...")
    for i, img_path in enumerate(images):
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(images)} images")
        
        results = model(img_path, verbose=False)
        pred_class = results[0].names[results[0].probs.top1]
        predictions.append(pred_class)
    
    return predictions


def calculate_category_metrics(y_true, y_pred, class_names):
    """Calculate precision, recall, and F1-score for each category."""
    # Get per-class metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=class_names, average=None, zero_division=0
    )
    
    # Create per-class dataframe
    per_class_df = pd.DataFrame({
        'Card': class_names,
        'Precision': precision * 100,
        'Recall': recall * 100,
        'F1-Score': f1 * 100,
        'Support': support
    })
    
    # Calculate category metrics
    numbered_mask = [cls in NUMBERED_CARDS for cls in class_names]
    face_mask = [cls in FACE_CARDS for cls in class_names]
    
    numbered_precision = np.average(precision[numbered_mask], weights=support[numbered_mask])
    numbered_recall = np.average(recall[numbered_mask], weights=support[numbered_mask])
    numbered_f1 = np.average(f1[numbered_mask], weights=support[numbered_mask])
    numbered_support = np.sum(support[numbered_mask])
    
    face_precision = np.average(precision[face_mask], weights=support[face_mask])
    face_recall = np.average(recall[face_mask], weights=support[face_mask])
    face_f1 = np.average(f1[face_mask], weights=support[face_mask])
    face_support = np.sum(support[face_mask])
    
    # Overall metrics
    overall_precision = np.average(precision, weights=support)
    overall_recall = np.average(recall, weights=support)
    overall_f1 = np.average(f1, weights=support)
    overall_support = np.sum(support)
    
    # Create category summary
    category_df = pd.DataFrame({
        'Card Category': ['Numbered (2-7)', 'Face (A,J,Q,K)', 'Overall'],
        'Precision': [numbered_precision * 100, face_precision * 100, overall_precision * 100],
        'Recall': [numbered_recall * 100, face_recall * 100, overall_recall * 100],
        'F1-Score': [numbered_f1 * 100, face_f1 * 100, overall_f1 * 100],
        'Sample Size': [numbered_support, face_support, overall_support]
    })
    
    return category_df, per_class_df


def plot_category_metrics(category_df, output_path='category_metrics.png'):
    """Create bar plot for category metrics."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(category_df))
    width = 0.25
    
    bars1 = ax.bar(x - width, category_df['Precision'], width, label='Precision', alpha=0.8)
    bars2 = ax.bar(x, category_df['Recall'], width, label='Recall', alpha=0.8)
    bars3 = ax.bar(x + width, category_df['F1-Score'], width, label='F1-Score', alpha=0.8)
    
    ax.set_xlabel('Card Category', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance by Card Category', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(category_df['Card Category'])
    ax.legend()
    ax.set_ylim([0, 105])
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Category metrics plot saved to {output_path}")
    plt.close()


def plot_per_class_metrics(per_class_df, output_path='per_class_metrics.png'):
    """Create detailed bar plot for per-class metrics."""
    fig, ax = plt.subplots(figsize=(20, 8))
    
    x = np.arange(len(per_class_df))
    width = 0.25
    
    bars1 = ax.bar(x - width, per_class_df['Precision'], width, label='Precision', alpha=0.8)
    bars2 = ax.bar(x, per_class_df['Recall'], width, label='Recall', alpha=0.8)
    bars3 = ax.bar(x + width, per_class_df['F1-Score'], width, label='F1-Score', alpha=0.8)
    
    ax.set_xlabel('Card Class', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance per Card Class', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(per_class_df['Card'], rotation=45, ha='right')
    ax.legend()
    ax.set_ylim([0, 105])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Per-class metrics plot saved to {output_path}")
    plt.close()


def plot_heatmap_metrics(per_class_df, output_path='metrics_heatmap.png'):
    """Create heatmap showing metrics for all classes."""
    # Prepare data for heatmap
    metrics_data = per_class_df[['Precision', 'Recall', 'F1-Score']].T
    metrics_data.columns = per_class_df['Card']
    
    fig, ax = plt.subplots(figsize=(20, 4))
    sns.heatmap(metrics_data, annot=True, fmt='.1f', cmap='RdYlGn', 
                vmin=0, vmax=100, cbar_kws={'label': 'Score (%)'}, ax=ax)
    ax.set_title('Performance Metrics Heatmap (All Cards)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Card Class', fontsize=12, fontweight='bold')
    ax.set_ylabel('Metric', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Metrics heatmap saved to {output_path}")
    plt.close()


def main():
    print("=" * 60)
    print("Card Classification Model Analysis")
    print("=" * 60)
    
    # Load model
    print(f"\nLoading model from {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    
    # Load validation data
    print(f"Loading validation data from {VAL_DATA_PATH}...")
    images, true_labels = load_validation_data(VAL_DATA_PATH)
    print(f"Found {len(images)} validation images across {len(set(true_labels))} classes")
    
    # Get predictions
    predictions = get_predictions(model, images)
    
    # Get class names (sorted)
    class_names = sorted(set(true_labels))
    
    # Calculate metrics
    print("\nCalculating metrics...")
    category_df, per_class_df = calculate_category_metrics(true_labels, predictions, class_names)
    
    # Display results
    print("\n" + "=" * 60)
    print("CATEGORY SUMMARY")
    print("=" * 60)
    print(category_df.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("PER-CLASS METRICS")
    print("=" * 60)
    print(per_class_df.to_string(index=False))
    
    # Save results
    output_dir = Path("runs/classify/sueca_cards_classifier")
    category_df.to_csv(output_dir / "category_metrics.csv", index=False)
    per_class_df.to_csv(output_dir / "per_class_metrics.csv", index=False)
    print(f"\nMetrics saved to:")
    print(f"  - {output_dir / 'category_metrics.csv'}")
    print(f"  - {output_dir / 'per_class_metrics.csv'}")
    
    # Generate plots
    print("\nGenerating visualizations...")
    plot_category_metrics(category_df, output_dir / "category_metrics.png")
    plot_per_class_metrics(per_class_df, output_dir / "per_class_metrics.png")
    plot_heatmap_metrics(per_class_df, output_dir / "metrics_heatmap.png")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
