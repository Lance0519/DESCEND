"""Vercel / WSGI entry for DESCEND Flask API."""

from flask import Flask, jsonify

# Top-level Flask instance required by @vercel/python detection.
app = Flask(__name__)


@app.get("/api/health")
def _fallback_health():
    return jsonify({"status": "ok", "mode": "fallback"})


@app.get("/")
def _fallback_root():
    return jsonify({"service": "DESCEND API", "health": "/api/health", "mode": "fallback"})


try:
    from descend import create_app

    app = create_app()
except Exception:
    import traceback

    _boot_error = traceback.format_exc()

    @app.get("/api/boot-error")
    def _boot_error_route():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Full DESCEND app failed to load",
                    "detail": _boot_error[-3500:],
                }
            ),
            500,
        )
