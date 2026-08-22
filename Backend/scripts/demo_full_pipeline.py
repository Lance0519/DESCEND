"""
Demo full pipeline: train model from processed training CSV, produce CV and holdout metrics,
write artifact JSON and joblib pipeline, and print summary for panel demonstration.
"""
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ml.modeling import train_model_from_dataset_path

DATASET = BACKEND_ROOT / "ml" / "datasets" / "processed" / "training_dataset.csv"
MODEL_OUT = BACKEND_ROOT / "models" / "demo_model.json"

if __name__ == "__main__":
    print("Training demo: reading dataset:", DATASET)
    artifact = train_model_from_dataset_path(DATASET, MODEL_OUT, seed=42, cv_repeats=1)

    metadata = artifact.get("metadata", {})
    print("\n=== Demo training complete ===")
    print(f"Dataset rows: {metadata.get('datasetRows')}")
    cv_mean = metadata.get('cvMetrics')
    holdout = metadata.get('holdoutMetrics')

    print("\n-- CV mean metrics --")
    if cv_mean:
        for k, v in cv_mean.items():
            print(f"  {k}: {v}")
    else:
        print("  (no CV metrics found)")

    print("\n-- Holdout test metrics --")
    if holdout:
        print(f"  optimizedThreshold: {holdout.get('optimizedThreshold')}")
        tm = holdout.get('testMetrics')
        if tm:
            for k in ['accuracy','precision','recall','f1Score','rocAuc','prAuc','brierScore']:
                print(f"    {k}: {tm.get(k)}")
    else:
        print("  (no holdout metrics found)")

    model_path = Path(MODEL_OUT).with_suffix('.joblib')
    print(f"\nWrote artifact: {MODEL_OUT}")
    print(f"Wrote pipeline: {model_path}")

    # Save a small summary JSON for panel display
    summary = {
        'datasetRows': metadata.get('datasetRows'),
        'cvMetrics': metadata.get('cvMetrics'),
        'holdoutMetrics': metadata.get('holdoutMetrics'),
        'topFeatures': metadata.get('topFeaturesRanked') or metadata.get('topFeatures') or artifact.get('featureImportances')
    }
    (MODEL_OUT.parent / 'demo_summary.json').write_text(json.dumps(summary, indent=2))
    print('Wrote summary:', MODEL_OUT.parent / 'demo_summary.json')
