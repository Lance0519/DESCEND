"""API blueprint factory with modular route organization."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import route modules to register sub-blueprints
from . import admin, assessment, auth, health, profile, tts

# Register blueprints in priority order
# Health checks first for uptime monitoring
api_bp.register_blueprint(health.health_bp)
# Authentication for all user-facing operations
api_bp.register_blueprint(auth.auth_bp, url_prefix="/auth")
# Main assessment functionality
api_bp.register_blueprint(assessment.assessment_bp)
# DESCEND profile / history / TTS
api_bp.register_blueprint(profile.profile_bp)
api_bp.register_blueprint(tts.tts_bp)
# Admin operations
api_bp.register_blueprint(admin.admin_bp)

__all__ = ["api_bp"]
