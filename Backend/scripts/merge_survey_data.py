"""Merge two raw survey CSV files without deduplicating by patient_id."""

import csv
from pathlib import Path


def merge_datasets(file1: Path, file2: Path, output_path: Path) -> dict:
    """
    Merge two CSV files by combining all rows.
    Remove only exact duplicates (identical rows).
    
    Returns dict with merge statistics.
    """
    
    if not file1.exists():
        raise FileNotFoundError(f"File 1 not found: {file1}")
    if not file2.exists():
        raise FileNotFoundError(f"File 2 not found: {file2}")
    
    # Read both files
    rows_file1 = []
    rows_file2 = []
    
    with file1.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows_file1 = list(reader)
    
    with file2.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows_file2 = list(reader)
    
    print(f"File 1 rows: {len(rows_file1)}")
    print(f"File 2 rows: {len(rows_file2)}")
    print(f"Total rows before dedup: {len(rows_file1) + len(rows_file2)}")
    
    # Combine all rows
    all_rows = rows_file1 + rows_file2
    
    # Remove exact duplicates (same row content)
    seen = set()
    unique_rows = []
    duplicates = 0
    
    for row in all_rows:
        # Create tuple of sorted items for comparison
        row_tuple = tuple(sorted(row.items()))
        if row_tuple not in seen:
            seen.add(row_tuple)
            unique_rows.append(row)
        else:
            duplicates += 1
    
    print(f"Exact duplicates removed: {duplicates}")
    print(f"Unique rows after dedup: {len(unique_rows)}")
    
    # Get fieldnames
    fieldnames = list(rows_file1[0].keys()) if rows_file1 else []
    
    if not fieldnames:
        raise ValueError("Could not determine fieldnames")
    
    # Write merged file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)
    
    return {
        'file1_rows': len(rows_file1),
        'file2_rows': len(rows_file2),
        'total_before': len(rows_file1) + len(rows_file2),
        'exact_duplicates': duplicates,
        'merged_rows': len(unique_rows),
    }


if __name__ == "__main__":
    import sys
    
    backend_dir = Path(__file__).resolve().parents[1]
    file1 = backend_dir / "ml" / "datasets" / "raw" / "survey_to_excel_raw_template - survey_to_excel_raw_template.csv"
    file2 = backend_dir / "ml" / "datasets" / "raw" / "survey_to_excel_raw_template - survey_to_excel_raw_template (1).csv"
    output = backend_dir / "ml" / "datasets" / "raw" / "survey_to_excel_raw_merged.csv"
    
    print("\n" + "="*70)
    print("MERGE SURVEY DATA (NO PATIENT_ID DEDUP)")
    print("="*70 + "\n")
    
    try:
        result = merge_datasets(file1, file2, output)
        
        print("\n" + "-"*70)
        print("MERGE RESULTS")
        print("-"*70)
        print(f"File 1 rows:              {result['file1_rows']}")
        print(f"File 2 rows:              {result['file2_rows']}")
        print(f"Total before dedup:       {result['total_before']}")
        print(f"Exact duplicates removed: {result['exact_duplicates']}")
        print(f"Final merged rows:        {result['merged_rows']}")
        
        print(f"\n✓ Merged file saved to:")
        print(f"  {output}")
        
        increase = result['merged_rows'] - result['file1_rows']
        if increase > 0:
            print(f"\n✓ Dataset expanded: {result['file1_rows']} → {result['merged_rows']} rows (+{increase})")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)
