"""API blueprint factory with modular route organization."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Health first (no ML imports) so /api/health can boot even if heavy routes fail.
from . import health

api_bp.register_blueprint(health.health_bp)


def register_heavy_routes() -> None:
    """Import and attach routes that pull in sklearn / larger deps."""
    from . import admin, assessment, auth, profile

    api_bp.register_blueprint(auth.auth_bp, url_prefix="/auth")
    api_bp.register_blueprint(assessment.assessment_bp)
    api_bp.register_blueprint(profile.profile_bp)
    api_bp.register_blueprint(admin.admin_bp)


__all__ = ["api_bp", "register_heavy_routes"]
