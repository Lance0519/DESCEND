"""Health check endpoints."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """System health check endpoint."""
    return jsonify({"status": "ok"})
