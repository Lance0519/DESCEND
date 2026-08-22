"""Diagnostic script to check dataset quality and identify issues causing perfect metrics."""

import csv
import sys
from pathlib import Path
from collections import Counter


def analyze_dataset(dataset_path: Path) -> None:
    """Analyze dataset for quality issues and separability."""
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("DATASET DIAGNOSTIC REPORT")
    print("="*70)
    print(f"\nDataset: {dataset_path}")
    print(f"File size: {dataset_path.stat().st_size / 1024:.1f} KB\n")
    
    # Read dataset
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Total rows: {len(rows)}")
    
    # Check for duplicates
    print("\n" + "-"*70)
    print("1. DUPLICATE ANALYSIS")
    print("-"*70)
    
    row_hashes = {}
    duplicates = 0
    for i, row in enumerate(rows):
        row_dict = dict(row)
        row_tuple = tuple(sorted(row_dict.items()))
        if row_tuple in row_hashes:
            duplicates += 1
            if duplicates == 1:
                print(f"  ⚠️  Found duplicate rows!")
                print(f"      First duplicate at row {i} (matches row {row_hashes[row_tuple]})")
        else:
            row_hashes[row_tuple] = i
    
    if duplicates == 0:
        print("  ✓ No exact duplicate rows found")
    else:
        print(f"  ❌ Found {duplicates} duplicate rows")
    
    # Class distribution
    print("\n" + "-"*70)
    print("2. CLASS DISTRIBUTION")
    print("-"*70)
    
    outcomes = [int(float(row.get("outcome", 0))) for row in rows]
    class_counts = Counter(outcomes)
    
    print(f"  Class 0 (Negative): {class_counts[0]} ({class_counts[0]/len(outcomes)*100:.1f}%)")
    print(f"  Class 1 (Positive): {class_counts[1]} ({class_counts[1]/len(outcomes)*100:.1f}%)")
    
    # Check for class imbalance
    ratio = max(class_counts.values()) / min(class_counts.values())
    if ratio > 5:
        print(f"  ⚠️  High class imbalance ratio: {ratio:.1f}:1")
    elif ratio > 2:
        print(f"  ⚠️  Moderate class imbalance ratio: {ratio:.1f}:1")
    else:
        print(f"  ✓ Reasonable class balance: {ratio:.1f}:1")
    
    # Feature statistics
    print("\n" + "-"*70)
    print("3. FEATURE STATISTICS")
    print("-"*70)
    
    if not rows:
        print("  ❌ No rows to analyze")
        return
    
    fieldnames = list(rows[0].keys())
    numeric_fields = [f for f in fieldnames if f != "outcome"]
    
    print(f"  Total features: {len(numeric_fields)}")
    
    # Check for constant features (no variance)
    constant_features = []
    for field in numeric_fields:
        try:
            values = [float(row[field]) for row in rows]
            unique_values = set(values)
            if len(unique_values) == 1:
                constant_features.append((field, values[0]))
        except (ValueError, KeyError):
            pass
    
    if constant_features:
        print(f"\n  ⚠️  CONSTANT FEATURES (no variance):")
        for feature, value in constant_features:
            print(f"      • {feature} = {value} (all rows)")
    else:
        print(f"  ✓ All features have variance")
    
    # Between-class feature comparison
    print("\n" + "-"*70)
    print("4. FEATURE SEPARATION ANALYSIS")
    print("-"*70)
    print("  Checking if features strongly separate the classes...")
    
    try:
        class_0_rows = [row for row, outcome in zip(rows, outcomes) if outcome == 0]
        class_1_rows = [row for row, outcome in zip(rows, outcomes) if outcome == 1]
        
        if not class_0_rows or not class_1_rows:
            print("  ❌ Cannot analyze - one class is empty")
        else:
            well_separated = []
            for field in numeric_fields[:5]:  # Sample first 5 features
                try:
                    class_0_vals = [float(row[field]) for row in class_0_rows]
                    class_1_vals = [float(row[field]) for row in class_1_rows]
                    
                    class_0_mean = sum(class_0_vals) / len(class_0_vals)
                    class_1_mean = sum(class_1_vals) / len(class_1_vals)
                    
                    class_0_std = (sum((v - class_0_mean)**2 for v in class_0_vals) / len(class_0_vals)) ** 0.5 or 0.001
                    class_1_std = (sum((v - class_1_mean)**2 for v in class_1_vals) / len(class_1_vals)) ** 0.5 or 0.001
                    
                    # Cohen's d effect size
                    pooled_std = ((class_0_std + class_1_std) / 2) or 0.001
                    cohens_d = abs(class_0_mean - class_1_mean) / pooled_std
                    
                    if cohens_d > 2.0:
                        well_separated.append((field, cohens_d))
                except (ValueError, KeyError, ZeroDivisionError):
                    pass
            
            if well_separated:
                print(f"  ⚠️  Features with STRONG separation (Cohen's d > 2.0):")
                for feature, d_value in sorted(well_separated, key=lambda x: x[1], reverse=True):
                    print(f"      • {feature}: d = {d_value:.2f}")
                print("\n      This suggests classes may be artificially/trivially separable")
            else:
                print("  ✓ No extreme feature separation detected")
    except Exception as e:
        print(f"  ⚠️  Could not analyze feature separation: {e}")
    
    # Data consistency checks
    print("\n" + "-"*70)
    print("5. DATA CONSISTENCY")
    print("-"*70)
    
    issues = []
    
    # Check for missing values
    for i, row in enumerate(rows[:5]):  # Check first 5 rows
        for key, value in row.items():
            if not value or value.strip() == "":
                issues.append(f"Empty value in row {i}, field {key}")
    
    if not issues:
        print("  ✓ No obvious missing values in sample")
    else:
        print(f"  ⚠️  Found issues:")
        for issue in issues[:3]:
            print(f"      • {issue}")
    
    # Data type consistency
    print("\n" + "-"*70)
    print("6. RECOMMENDATIONS")
    print("-"*70)
    
    recommendations = [
        "• Check if dataset is synthetic or real patient data",
        "• Verify ground truth labels (outcome column) are correct",
        "• Check for data leakage in feature engineering",
        "• Look for duplicated or near-duplicate patient records",
        "• Validate that features don't directly encode the outcome",
        "• Consider testing on external validation dataset",
        "• Review feature engineering code for errors",
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[1]
    dataset_path = backend_dir / "ml" / "datasets" / "processed" / "training_dataset.csv"
    
    try:
        analyze_dataset(dataset_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
