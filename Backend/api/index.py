"""Vercel serverless entry for DESCEND Flask API."""

import sys
import traceback
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app import create_app

    app = create_app()
except Exception:
    # Surface cold-start failures instead of a blank FUNCTION_INVOCATION_FAILED page.
    _tb = traceback.format_exc()
    from flask import Flask

    app = Flask(__name__)

    @app.get("/")
    @app.get("/api/health")
    def _boot_error():
        return (
            {
                "status": "error",
                "message": "DESCEND API failed to start",
                "detail": _tb[-4000:],
            },
            500,
        )
