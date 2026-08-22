"""Application configuration with absolute path resolution."""

import os
import secrets
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


# ============== ABSOLUTE PATH RESOLUTION ==============
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
INSTANCE_DIR = BACKEND_DIR / "instance"
ML_DIR = BACKEND_DIR / "ml"

# Absolute paths for ML artifacts
MODELS_DIR = ML_DIR / "models"
DATASETS_DIR = ML_DIR / "datasets"

# Default model and dataset with absolute, non-relative paths
DEFAULT_MODEL = MODELS_DIR / "t2dm_risk_model.json"
DEFAULT_DATASET = INSTANCE_DIR / "datasets" / "uploaded_dataset.csv"

# ============== ENVIRONMENT LOADING ==============
# Load local .env files only when not on Vercel. On Vercel, dashboard env vars
# must win — never override them with a bundled .env (override=True is unsafe there).
env_files = [
    BACKEND_DIR / ".env",
    BACKEND_DIR / ".env.local",
    BACKEND_DIR / ".env.mysql",
]

if not os.getenv("VERCEL"):
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)


def _normalize_database_uri(uri: str) -> str:
    """Normalize Postgres URIs for SQLAlchemy + Supabase SSL."""
    value = uri.strip()
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://") :]
    if value.startswith("postgresql://") and "+psycopg2" not in value.split("://", 1)[0]:
        value = "postgresql+psycopg2://" + value[len("postgresql://") :]
    # Supabase (and most hosted Postgres) need SSL from serverless hosts.
    if value.startswith("postgresql") and "sslmode=" not in value:
        sep = "&" if "?" in value else "?"
        value = f"{value}{sep}sslmode=require"
    return value


def _build_database_uri() -> str:
    """Build SQLAlchemy database URI with explicit priority."""
    # Priority 0: Explicit SQLALCHEMY_DATABASE_URI (for testing/custom setups)
    explicit_db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    if explicit_db_uri:
        return _normalize_database_uri(explicit_db_uri)

    # Priority 1: Explicit DATABASE_URL environment variable
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return _normalize_database_uri(explicit_url)

    # Priority 2: MySQL
    mysql_host = os.getenv("MYSQL_HOST", "")
    mysql_db = os.getenv("MYSQL_DB", "")
    mysql_user = os.getenv("MYSQL_USER", "")
    mysql_pass = os.getenv("MYSQL_PASSWORD", "")
    mysql_port = os.getenv("MYSQL_PORT", "3306")

    if mysql_host and mysql_db and mysql_user:
        encoded_password = quote_plus(mysql_pass)
        return f"mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_db}"

    # Priority 3: SQLite — use /tmp on Vercel (read-only app filesystem)
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/descend_vercel.db"
    sqlite_path = INSTANCE_DIR / "t2dm_dev.db"
    return f"sqlite:///{sqlite_path}"


class Config:
    """Application configuration with absolute path resolution."""
    
    # ============== CORE SETTINGS ==============
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ============== FRONTEND SETTINGS ==============
    # Comma-separated list (Vite may use 5174+ if 5173 is busy)
    FRONTEND_ORIGIN = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://localhost:5174",
    )
    
    # ============== ABSOLUTE PATHS FOR ML ARTIFACTS ==============
    # Use absolute Path objects, force conversion to string for Flask
    MODEL_PATH = Path(
        os.getenv("MODEL_PATH", str(DEFAULT_MODEL.absolute()))
    ).absolute()
    DATASET_PATH = Path(
        os.getenv("DATASET_PATH", str(DEFAULT_DATASET.absolute()))
    ).absolute()
    
    # ============== FEATURE FLAGS & CONSTRAINTS ==============
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "1048576"))
    AUTH_TOKEN_MAX_AGE = int(os.getenv("AUTH_TOKEN_MAX_AGE", "604800"))
    PASSWORD_RESET_MAX_AGE = int(os.getenv("PASSWORD_RESET_MAX_AGE", "3600"))
    LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    EXPOSE_RESET_TOKEN_PREVIEW = (
        os.getenv("EXPOSE_RESET_TOKEN_PREVIEW", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
