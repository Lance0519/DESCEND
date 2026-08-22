"""Vercel serverless entry for DESCEND Flask API."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app

app = create_app()
