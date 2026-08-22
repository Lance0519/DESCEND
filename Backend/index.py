"""Vercel / WSGI entry for DESCEND Flask API."""

from __future__ import annotations

import traceback

from flask import Flask, jsonify

_boot_error: str | None = None


def _fallback_app(error: str) -> Flask:
    """Always export a WSGI app so Vercel can boot and show the real error."""
    fal = Flask(__name__)

    @fal.get("/")
    @fal.get("/api/health")
    def health():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "DESCEND API failed to start",
                    "detail": error[-3500:],
                }
            ),
            500,
        )

    return fal


try:
    from descend import create_app

    app = create_app()
except Exception:
    _boot_error = traceback.format_exc()
    app = _fallback_app(_boot_error)
