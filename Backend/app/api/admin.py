"""Admin panel endpoints."""

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import desc

from ..extensions import db
from ..models import Assessment, User
from ..ml.predictor import (
    get_model_evaluation,
    train_model_from_dataset,
)
from .auth import _get_current_user, _serialize_user
from .assessment import (
    _history_export_rows,
    _parse_iso_date,
    _csv_response,
    _serialize_assessment,
    parse_stored_assessment_payload,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def _require_admin() -> User:
    """Require admin role and return user."""
    user = _get_current_user(required=True)
    if user.role != "admin":
        raise PermissionError("Admin access is required.")
    return user


def _filter_assessments_for_admin(
    assessments: List[Assessment],
    search: str,
    risk_band: str,
    start_date: str,
    end_date: str,
) -> List[Assessment]:
    """Filter assessments by criteria."""
    lowered_search = search.strip().lower()
    start_dt = _parse_iso_date(start_date)
    end_dt = _parse_iso_date(end_date, end_of_day=True)
    filtered: List[Assessment] = []

    for assessment in assessments:
        serialized = _serialize_assessment(assessment)
        if lowered_search:
            user_email = assessment.user.email.lower() if assessment.user else "guest"
            matches_search = (
                lowered_search in user_email
                or lowered_search in str(assessment.id)
                or lowered_search in assessment.title.lower()
            )
            if not matches_search:
                continue

        if risk_band and serialized["overallRiskBand"] != risk_band:
            continue
        if start_dt and assessment.created_at < start_dt:
            continue
        if end_dt and assessment.created_at > end_dt:
            continue
        filtered.append(assessment)

    return filtered


def _top_risk_patterns(assessments: List[Assessment]) -> List[dict]:
    """Analyze top risk patterns in assessments."""
    counters = {
        "family_history_positive": 0,
        "high_bmi": 0,
        "hypertension_history": 0,
        "parent_t2dm_or_unsure": 0,
    }
    for assessment in assessments:
        try:
            payload, _ = parse_stored_assessment_payload(assessment.payload_json)
        except (TypeError, AttributeError):
            continue
        if not payload:
            continue
        family_history = payload.get("familyHistory", {})
        personal = payload.get("personalInfo", {})
        if any(value == "yes" for value in family_history.values()):
            counters["family_history_positive"] += 1
        if assessment.bmi >= 25:
            counters["high_bmi"] += 1
        if personal.get("diagnosedHypertension") in {"yes", "unsure"}:
            counters["hypertension_history"] += 1
        if personal.get("diagnosedT2dm") in {"yes", "unsure"}:
            counters["parent_t2dm_or_unsure"] += 1
    labels = {
        "family_history_positive": "Positive family diabetes history",
        "high_bmi": "BMI above ideal range",
        "hypertension_history": "Parent hypertension history",
        "parent_t2dm_or_unsure": "Parent has or is unsure of T2DM diagnosis",
    }
    return [
        {"pattern": labels[key], "count": value}
        for key, value in sorted(counters.items(), key=lambda item: item[1], reverse=True)
    ]


def _build_admin_analytics(assessments: List[Assessment]) -> dict:
    """Build analytics summary from assessments."""
    band_counts = {"Low": 0, "Moderate": 0, "High": 0}
    monthly_counts: dict = {}
    total_probability = 0.0
    total_bmi = 0.0
    guest_count = 0
    saved_count = 0

    for assessment in assessments:
        serialized = _serialize_assessment(assessment)
        band_counts[serialized["overallRiskBand"]] += 1
        total_probability += serialized["averagePercentage"]
        total_bmi += serialized["bmi"]
        month_key = assessment.created_at.strftime("%Y-%m")
        monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        if assessment.user_id is None:
            guest_count += 1
        else:
            saved_count += 1

    month_items = [
        {"month": month, "count": count}
        for month, count in sorted(monthly_counts.items())[-6:]
    ]
    count = len(assessments)
    return {
        "averageProbability": round(total_probability / count, 1) if count else 0.0,
        "averageBmi": round(total_bmi / count, 2) if count else 0.0,
        "riskBandCounts": band_counts,
        "monthlyAssessments": month_items,
        "topRiskPatterns": _top_risk_patterns(assessments),
        "guestVsRegistered": {"guest": guest_count, "registered": saved_count},
    }


# ============= ENDPOINTS =============


@admin_bp.get("/overview")
def admin_overview():
    """Get admin dashboard overview."""
    try:
        user = _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    search = request.args.get("search", "")
    risk_band = request.args.get("riskBand", "")
    start_date = request.args.get("startDate", "")
    end_date = request.args.get("endDate", "")

    users = User.query.order_by(desc(User.created_at)).limit(12).all()
    all_assessments = Assessment.query.order_by(desc(Assessment.created_at)).all()
    filtered_assessments = _filter_assessments_for_admin(
        all_assessments, search, risk_band, start_date, end_date
    )
    assessments = filtered_assessments[:15]

    recent_assessments = []
    for assessment in assessments:
        serialized = _serialize_assessment(assessment)
        recent_assessments.append(
            {
                **serialized,
                "userEmail": assessment.user.email if assessment.user else "Guest",
            }
        )

    return jsonify(
        {
            "stats": {
                "userCount": User.query.count(),
                "assessmentCount": Assessment.query.count(),
                "adminCount": User.query.filter_by(role="admin").count(),
                "guestAssessmentCount": Assessment.query.filter(
                    Assessment.user_id.is_(None)
                ).count(),
                "savedAssessmentCount": Assessment.query.filter(
                    Assessment.user_id.is_not(None)
                ).count(),
                "disabledUserCount": User.query.filter_by(is_active=False).count(),
            },
            "analytics": _build_admin_analytics(filtered_assessments),
            "filters": {
                "search": search,
                "riskBand": risk_band,
                "startDate": start_date,
                "endDate": end_date,
            },
            "recentUsers": [_serialize_user(item) for item in users],
            "recentAssessments": recent_assessments,
        }
    )


@admin_bp.get("/export")
def admin_export():
    """Export all assessments as CSV."""
    try:
        _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    search = request.args.get("search", "")
    risk_band = request.args.get("riskBand", "")
    start_date = request.args.get("startDate", "")
    end_date = request.args.get("endDate", "")
    assessments = _filter_assessments_for_admin(
        Assessment.query.order_by(desc(Assessment.created_at)).all(),
        search,
        risk_band,
        start_date,
        end_date,
    )
    rows = _history_export_rows(assessments)
    for row, assessment in zip(rows, assessments):
        row["user_email"] = assessment.user.email if assessment.user else "guest"
    return _csv_response("all-assessments-export.csv", rows)


@admin_bp.get("/users")
def admin_users():
    """Get all users."""
    try:
        _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    search = request.args.get("search", "").strip().lower()
    users = User.query.order_by(desc(User.created_at)).all()
    if search:
        users = [
            user
            for user in users
            if search in user.email.lower() or search in user.name.lower()
        ]
    return jsonify({"items": [_serialize_user(user) for user in users]})


@admin_bp.patch("/users/<int:user_id>/role")
def update_user_role(user_id: int):
    """Update user role."""
    try:
        admin = _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404

    payload = request.get_json(silent=True) or {}
    role = str(payload.get("role", "")).strip().lower()
    if role not in {"admin", "user"}:
        return jsonify({"message": "Role must be admin or user."}), 400
    if admin.id == user.id and role != "admin":
        return (
            jsonify({"message": "You cannot remove your own admin access."}),
            400,
        )

    user.role = role
    db.session.commit()
    return jsonify({"message": "User role updated.", "user": _serialize_user(user)})


@admin_bp.patch("/users/<int:user_id>/status")
def update_user_status(user_id: int):
    """Update user active status."""
    try:
        admin = _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404

    payload = request.get_json(silent=True) or {}
    is_active = bool(payload.get("isActive", True))
    if admin.id == user.id and not is_active:
        return (
            jsonify({"message": "You cannot disable your own account."}),
            400,
        )

    user.is_active = is_active
    if is_active:
        user.failed_login_attempts = 0
        user.locked_until = None
    db.session.commit()
    return jsonify({"message": "User status updated.", "user": _serialize_user(user)})


@admin_bp.post("/users/<int:user_id>/reset-password")
def admin_reset_password(user_id: int):
    """Generate temporary password for user."""
    try:
        _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404

    temporary_password = f"Temp{secrets.token_hex(4)}!9A"
    user.set_password(temporary_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.session.commit()
    return jsonify(
        {
            "message": "Temporary password generated.",
            "temporaryPassword": temporary_password,
            "user": _serialize_user(user),
        }
    )


@admin_bp.get("/model/evaluation")
def admin_model_evaluation():
    """Get model evaluation metrics."""
    try:
        _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    return jsonify(get_model_evaluation())


@admin_bp.post("/model/upload")
def admin_model_upload():
    """Upload dataset and train model."""
    try:
        _require_admin()
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"message": str(exc)}), 403

    dataset_path = Path(current_app.config["DATASET_PATH"])
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    if request.files.get("file"):
        uploaded_file = request.files["file"]
        uploaded_file.save(dataset_path)
    else:
        payload = request.get_json(silent=True) or {}
        csv_content = str(payload.get("csvContent", ""))
        if not csv_content.strip():
            return (
                jsonify({"message": "No dataset file or CSV content was provided."}),
                400,
            )
        dataset_path.write_text(csv_content, encoding="utf-8")

    try:
        artifact = train_model_from_dataset(
            dataset_path, Path(current_app.config["MODEL_PATH"])
        )
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"message": str(exc)}), 400

    return jsonify(
        {
            "message": "Dataset uploaded and model updated.",
            "evaluation": artifact.get("metadata", {}),
        }
    )
