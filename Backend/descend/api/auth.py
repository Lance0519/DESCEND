"""Authentication endpoints and utilities."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__)
PASSWORD_SPECIALS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?"


def _now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def _serializer() -> URLSafeTimedSerializer:
    """Create token serializer with app-specific salt."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="t2dm-auth")


def _normalize_email(value: str) -> str:
    """Normalize email to lowercase and strip whitespace."""
    return value.strip().lower()


def _hash_token(token: str) -> str:
    """Hash token using SHA256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_token(user: User) -> str:
    """Create authentication token for user."""
    return _serializer().dumps({"user_id": user.id, "role": user.role})


def _get_token_from_request() -> Optional[str]:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip() or None


def _get_current_user(required: bool = False) -> Optional[User]:
    """Get authenticated Flask user from a legacy itsdangerous token.

    Frontend login uses Supabase JWTs. Those are verified separately via
    ``verify_bearer_token`` on estimate/predict. When ``required`` is False,
    an unrecognized Bearer token must not block scoring — treat as anonymous.
    """
    token = _get_token_from_request()
    if not token:
        if required:
            raise ValueError("Authentication is required.")
        return None

    try:
        payload = _serializer().loads(
            token, max_age=current_app.config["AUTH_TOKEN_MAX_AGE"]
        )
    except SignatureExpired as exc:
        if not required:
            return None
        raise ValueError("Your session has expired. Please log in again.") from exc
    except BadSignature as exc:
        if not required:
            return None
        raise ValueError("Invalid authentication token.") from exc

    user = db.session.get(User, payload.get("user_id"))
    if not user:
        if not required:
            return None
        raise ValueError("The account associated with this session no longer exists.")
    if not user.is_active:
        raise ValueError("This account is disabled. Contact an administrator.")
    return user


def _validate_password(password: str, email: str, name: str) -> list:
    """Validate password against security requirements."""
    issues: list = []
    lowered_password = password.lower()

    if len(password) < 12:
        issues.append("Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        issues.append("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        issues.append("Password must include at least one lowercase letter.")
    if not re.search(r"\d", password):
        issues.append("Password must include at least one number.")
    if not re.search(f"[{re.escape(PASSWORD_SPECIALS)}]", password):
        issues.append("Password must include at least one special character.")
    if " " in password:
        issues.append("Password must not contain spaces.")

    email_name = email.split("@", 1)[0].lower()
    if email_name and email_name in lowered_password:
        issues.append("Password must not contain the email name.")

    condensed_name = re.sub(r"\s+", "", name).lower()
    if condensed_name and len(condensed_name) >= 3 and condensed_name in lowered_password:
        issues.append("Password must not contain your name.")

    return issues


def _serialize_user(user: User) -> dict:
    """Serialize user to JSON-compatible dict."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "isActive": user.is_active,
        "failedLoginAttempts": user.failed_login_attempts,
        "lockedUntil": user.locked_until.isoformat() + "Z" if user.locked_until else None,
        "lastLoginAt": user.last_login_at.isoformat() + "Z" if user.last_login_at else None,
        "createdAt": user.created_at.isoformat() + "Z",
    }


def _register_failed_login(user: User) -> Tuple[int, str]:
    """Register failed login attempt and lock if needed."""
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
        user.locked_until = _now() + timedelta(
            minutes=current_app.config["LOGIN_LOCK_MINUTES"]
        )
        db.session.commit()
        return 423, "Account locked due to repeated failed login attempts. Try again later."
    db.session.commit()
    return 401, "Invalid email or password."


def _reset_login_lock(user: User) -> None:
    """Clear login lock and update last login time."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _now()
    db.session.commit()


# ============= ENDPOINTS =============


@auth_bp.post("/register")
def register():
    """Register new user account."""
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = _normalize_email(str(payload.get("email", "")))
    password = str(payload.get("password", ""))

    if len(name) < 2:
        return jsonify({"message": "Name must be at least 2 characters long."}), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"message": "Enter a valid email address."}), 400
    if db.session.query(User.id).filter_by(email=email).first():
        return jsonify({"message": "An account with that email already exists."}), 409

    password_issues = _validate_password(password, email, name)
    if password_issues:
        return (
            jsonify(
                {
                    "message": "Password does not meet security requirements.",
                    "issues": password_issues,
                }
            ),
            400,
        )

    role = "user"
    has_admin_account = db.session.query(User.id).filter_by(role="admin").first() is not None
    has_any_user = db.session.query(User.id).first() is not None
    bootstrap_email = current_app.config.get("INITIAL_ADMIN_EMAIL", "")
    if not has_any_user and not has_admin_account:
        role = "admin"
    elif bootstrap_email and email == bootstrap_email and not has_admin_account:
        role = "admin"

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return (
        jsonify(
            {
                "token": _create_token(user),
                "user": _serialize_user(user),
                "message": "Account created successfully.",
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login():
    """Authenticate user and return token."""
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(str(payload.get("email", "")))
    password = str(payload.get("password", ""))

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Invalid email or password."}), 401
    if not user.is_active:
        return (
            jsonify(
                {"message": "This account is disabled. Contact an administrator."}
            ),
            403,
        )
    if user.locked_until and user.locked_until > _now():
        return (
            jsonify(
                {
                    "message": "Account is temporarily locked due to repeated failed logins."
                }
            ),
            423,
        )
    if not user.check_password(password):
        status_code, message = _register_failed_login(user)
        return jsonify({"message": message}), status_code

    _reset_login_lock(user)
    return jsonify(
        {
            "token": _create_token(user),
            "user": _serialize_user(user),
            "message": "Login successful.",
        }
    )


@auth_bp.post("/forgot-password")
def forgot_password():
    """Initiate password reset flow."""
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(str(payload.get("email", "")))
    user = User.query.filter_by(email=email).first()
    generic_message = "If the account exists, a password reset link has been prepared."
    if not user or not user.is_active:
        return jsonify({"message": generic_message})

    reset_token = secrets.token_urlsafe(24)
    user.reset_token_hash = _hash_token(reset_token)
    user.reset_token_expires_at = _now() + timedelta(
        seconds=current_app.config["PASSWORD_RESET_MAX_AGE"]
    )
    db.session.commit()

    response_payload = {"message": generic_message}
    if current_app.config.get("EXPOSE_RESET_TOKEN_PREVIEW", False):
        frontend_origin = current_app.config["FRONTEND_ORIGIN"]
        response_payload["resetTokenPreview"] = reset_token
        response_payload["resetLinkPreview"] = (
            f"{frontend_origin}/reset-password?token={reset_token}"
        )
    return jsonify(response_payload)


@auth_bp.post("/reset-password")
def reset_password():
    """Complete password reset with token."""
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token", ""))
    new_password = str(payload.get("newPassword", ""))
    token_hash = _hash_token(token)
    user = User.query.filter_by(reset_token_hash=token_hash).first()

    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < _now():
        return jsonify({"message": "Reset token is invalid or expired."}), 400

    password_issues = _validate_password(new_password, user.email, user.name)
    if password_issues:
        return (
            jsonify(
                {
                    "message": "Password does not meet security requirements.",
                    "issues": password_issues,
                }
            ),
            400,
        )

    user.set_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    return jsonify({"message": "Password reset successfully."})


@auth_bp.get("/me")
def auth_me():
    """Get current authenticated user."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    return jsonify({"user": _serialize_user(user)})


@auth_bp.post("/change-password")
def change_password():
    """Change password for authenticated user."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("currentPassword", ""))
    new_password = str(payload.get("newPassword", ""))

    if not user.check_password(current_password):
        return jsonify({"message": "Current password is incorrect."}), 400
    if current_password == new_password:
        return (
            jsonify(
                {"message": "New password must be different from the current password."}
            ),
            400,
        )

    password_issues = _validate_password(new_password, user.email, user.name)
    if password_issues:
        return (
            jsonify(
                {
                    "message": "Password does not meet security requirements.",
                    "issues": password_issues,
                }
            ),
            400,
        )

    user.set_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.session.commit()
    return jsonify({"message": "Password updated successfully."})
