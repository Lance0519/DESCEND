"""Run the full automation pipeline: merge uploaded survey and optionally train.

Usage examples:
  # Merge uploaded raw into processed training CSV (safe default)
  python backend/scripts/run_full_pipeline.py --merge

  # Merge then train with default options
  python backend/scripts/run_full_pipeline.py --merge --train

  # Pass additional train args (quoted)
  python backend/scripts/run_full_pipeline.py --merge --train --train-args "--balance oversample --cv-repeats 2"
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SCRIPT = ROOT / "train.py"
MERGE_SCRIPT = Path(__file__).resolve().parent / "merge_uploaded_to_training.py"


def run_merge():
    print("Running merge step...")
    # invoke as module to preserve same interpreter context
    import importlib.util
    spec = importlib.util.spec_from_file_location("merge_module", str(MERGE_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


def run_train(train_args: str | None = None):
    cmd = ["python", str(TRAIN_SCRIPT)]
    if train_args:
        # split respecting quotes
        cmd += shlex.split(train_args)
    print("Launching training:", " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"Training failed (exit {proc.returncode}).")


def main():
    parser = argparse.ArgumentParser(description="Run full pipeline: merge uploaded survey and optionally train model")
    parser.add_argument("--merge", action="store_true", help="Run merge of uploaded survey into processed training dataset")
    parser.add_argument("--train", action="store_true", help="Run model training after merge")
    parser.add_argument("--train-args", type=str, default="", help="Extra args to pass to backend/train.py (quoted string)")
    args = parser.parse_args()

    if not args.merge and not args.train:
        print("Nothing to do. Use --merge and/or --train.")
        return

    if args.merge:
        run_merge()

    if args.train:
        run_train(args.train_args)


if __name__ == '__main__':
    main()
