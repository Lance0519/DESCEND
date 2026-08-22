"""Vercel entry — keep import-light so builds succeed; load full app on first request."""

from __future__ import annotations

from flask import Flask, jsonify, request

app = Flask(__name__)

_backend = None
_backend_error: str | None = None


def get_backend():
    """Lazy-load the full Flask app (sklearn, DB, routes)."""
    global _backend, _backend_error
    if _backend is None and _backend_error is None:
        try:
            from descend import create_app

            _backend = create_app()
        except Exception:
            import traceback

            _backend_error = traceback.format_exc()
    return _backend


@app.get("/api/health")
def health():
    backend = get_backend()
    if backend is None:
        return (
            jsonify(
                {
                    "status": "degraded",
                    "message": "Core API failed to load",
                    "detail": (_backend_error or "")[-3500:],
                }
            ),
            500,
        )
    return jsonify({"status": "ok", "service": "DESCEND API"})


@app.get("/")
def root():
    return jsonify({"service": "DESCEND API", "health": "/api/health", "predict": "/api/predict"})


@app.route(
    "/<path:path>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
def proxy(path: str):
    """Forward all other paths to the full DESCEND Flask app."""
    if request.path == "/api/health":
        return health()

    backend = get_backend()
    if backend is None:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Core API failed to load",
                    "detail": (_backend_error or "")[-3500:],
                }
            ),
            500,
        )

    with backend.request_context(request.environ):
        try:
            return backend.full_dispatch_request()
        except Exception:
            import traceback

            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Request handling failed",
                        "detail": traceback.format_exc()[-3500:],
                    }
                ),
                500,
            )
