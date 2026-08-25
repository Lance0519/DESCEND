"""Flask application factory with absolute path resolution."""

import logging
import os
from pathlib import Path

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from .bootstrap import ensure_database_schema
from .config import Config
from .extensions import cors, db

logger = logging.getLogger(__name__)


def _is_vercel() -> bool:
    return bool(os.getenv("VERCEL"))


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Use absolute paths from config (no relative path assumptions)
    instance_path = Path(app.instance_path)
    model_path = Path(app.config["MODEL_PATH"])
    dataset_path = Path(app.config["DATASET_PATH"])

    # Vercel filesystem is read-only except /tmp — skip local mkdir there.
    if not _is_vercel():
        instance_path.mkdir(parents=True, exist_ok=True)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        dataset_path.parent.mkdir(parents=True, exist_ok=True)

    # If a MySQL URI is configured, require a reachable MySQL server locally.
    # On Vercel, skip hard-fail so mis-set MySQL env cannot crash the function.
    _db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if _db_uri and _db_uri.startswith("mysql") and not _is_vercel():
        try:
            test_engine = create_engine(_db_uri)
            conn = test_engine.connect()
            conn.close()
        except OperationalError as exc:
            raise RuntimeError(
                "Unable to connect to configured MySQL server. "
                "Ensure MYSQL_HOST, MYSQL_DB, MYSQL_USER and MYSQL_PASSWORD "
                "are correctly set and the server is accessible."
            ) from exc

    # Initialize extensions
    db.init_app(app)
    _origins = [
        o.strip()
        for o in str(app.config["FRONTEND_ORIGIN"]).split(",")
        if o.strip()
    ]
    # Always allow known production frontends (env may lag behind).
    _origins.append("https://descendt2dm.netlify.app")
    _origins.append("https://descendt2dm.me")
    _origins.append("https://www.descendt2dm.me")
    # Any Vite port when FLASK_ENV is development (5173, 5174, …); avoids shell env
    # overriding .env and breaking CORS (load_dotenv override=True fixes that too).
    _flask_env = os.getenv("FLASK_ENV", "development").strip().lower()
    if _flask_env in ("development", "dev") or _is_vercel():
        _origins.extend(
            [
                r"^http://localhost:\d+$",
                r"^http://127\.0\.0\.1:\d+$",
            ]
        )
    if _is_vercel():
        _origins.append(r"^https://[a-z0-9-]+\.netlify\.app$")
        _origins.append(r"^https://([a-z0-9-]+\.)?descendt2dm\.me$")
    # De-dupe while preserving order
    _seen: set[str] = set()
    _unique_origins: list[str] = []
    for origin in _origins:
        if origin not in _seen:
            _seen.add(origin)
            _unique_origins.append(origin)

    cors.init_app(
        app,
        resources={
            r"^/api/.*": {
                "origins": _unique_origins,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            },
        },
    )

    # Build API blueprint fully before attaching it to the app.
    from .api import api_bp, register_heavy_routes

    try:
        register_heavy_routes()
    except Exception:
        logger.exception("Heavy API routes failed to load")
        if not _is_vercel():
            raise

    app.register_blueprint(api_bp, url_prefix="/api")

    # Ensure models are registered for create_all even if heavy routes failed.
    from . import models as _models  # noqa: F401

    # Initialize database (do not crash the whole serverless function on Vercel
    # if Postgres is misconfigured — /api/health and /api/predict can still run).
    with app.app_context():
        try:
            db.create_all()
            ensure_database_schema()
        except Exception:
            # Never fail process startup on schema issues (Vercel build/runtime,
            # bad Postgres URI, etc.). Predict can still run without DB writes.
            logger.exception("Database schema init failed")

    @app.get("/")
    def root():
        """Avoid a bare-domain crash page; point callers at the API."""
        return {
            "service": "DESCEND API",
            "health": "/api/health",
            "predict": "/api/predict",
        }

    return app
