"""Assessment and prediction endpoints."""

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import List, Optional

from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy import desc

from ..extensions import db
from ..ml.feature_builder import build_base_features
from ..ml.predictor import (
    get_model_evaluation,
    predict_assessment,
    respondent_probability_from_scenario_lookup,
    respondent_risk_band_for_display,
    risk_band_for_probability,
    train_model_from_dataset,
)
from ..models import Assessment, PredictionResult, User
from .auth import _get_current_user
from .profile import save_assessment_for_user
from ..supabase_auth import verify_bearer_token

assessment_bp = Blueprint("assessment", __name__)

_ASSESSMENT_STORE_VERSION = 2


def parse_stored_assessment_payload(payload_json: str) -> tuple[dict, dict | None]:
    """Split stored JSON into the original form payload and optional prediction meta."""
    if not payload_json or not str(payload_json).strip():
        return {}, None
    try:
        data = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}, None
    if not isinstance(data, dict):
        return {}, None
    if data.get("v") == _ASSESSMENT_STORE_VERSION and isinstance(data.get("form"), dict):
        meta = {
            "respondentProbability": data.get("respondentProbability"),
            "lineageScenarioMultiplier": data.get("lineageScenarioMultiplier"),
        }
        return data["form"], meta
    return data, None


def _now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def _serialize_assessment(assessment: Assessment) -> dict:
    """Serialize assessment to JSON-compatible dict."""
    predictions = sorted(assessment.predictions, key=lambda item: item.id)
    lookup = {item.target_key: item.probability for item in predictions}
    _, meta = parse_stored_assessment_payload(assessment.payload_json or "{}")
    lineage_mult = None
    if meta and meta.get("lineageScenarioMultiplier") is not None:
        lineage_mult = float(meta["lineageScenarioMultiplier"])
    if meta and meta.get("respondentProbability") is not None:
        average_probability = float(meta["respondentProbability"])
    else:
        average_probability = respondent_probability_from_scenario_lookup(lookup, lineage_mult)

    form_payload, _ = parse_stored_assessment_payload(assessment.payload_json or "{}")
    if form_payload and form_payload.get("personalInfo"):
        try:
            _, derived = build_base_features(form_payload)
            overall_band, _ = respondent_risk_band_for_display(average_probability, derived)
        except (TypeError, ValueError, KeyError):
            overall_band = risk_band_for_probability(average_probability)
    else:
        overall_band = risk_band_for_probability(average_probability)

    return {
        "assessmentId": assessment.id,
        "title": assessment.title,
        "createdAt": assessment.created_at.isoformat() + "Z",
        "updatedAt": assessment.updated_at.isoformat() + "Z",
        "bmi": round(assessment.bmi, 2),
        "weightedFamilyScore": round(assessment.weighted_family_score, 3),
        "overallRiskBand": overall_band,
        "averagePercentage": round(average_probability * 100, 1),
        "predictions": [
            {
                "key": item.target_key,
                "label": item.target_label,
                "probability": item.probability,
                "percentage": round(item.probability * 100, 1),
                "riskBand": risk_band_for_probability(item.probability),
            }
            for item in predictions
        ],
    }


def _parse_iso_date(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    """Parse ISO format date string."""
    if not value:
        return None
    try:
        if end_of_day:
            return datetime.fromisoformat(f"{value}T23:59:59")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _history_query(user: User, search: str, start_date: str, end_date: str) -> List[Assessment]:
    """Query user's assessments with filtering."""
    query = Assessment.query.filter_by(user_id=user.id)
    start_dt = _parse_iso_date(start_date)
    end_dt = _parse_iso_date(end_date, end_of_day=True)
    if start_dt:
        query = query.filter(Assessment.created_at >= start_dt)
    if end_dt:
        query = query.filter(Assessment.created_at <= end_dt)

    assessments = query.order_by(desc(Assessment.created_at)).all()
    lowered_search = search.strip().lower()
    if not lowered_search:
        return assessments
    return [
        item
        for item in assessments
        if lowered_search in item.title.lower() or lowered_search in str(item.id)
    ]


def _history_export_rows(assessments: List[Assessment]) -> List[dict]:
    """Convert assessments to CSV-compatible rows."""
    rows: List[dict] = []
    prediction_keys = [
        ("male_child", "Male Child"),
        ("female_child", "Female Child"),
        ("male_grandchild", "Male Grandchild"),
        ("female_grandchild", "Female Grandchild"),
    ]

    for assessment in assessments:
        serialized = _serialize_assessment(assessment)
        row = {
            "assessment_id": serialized["assessmentId"],
            "title": serialized["title"],
            "created_at": serialized["createdAt"],
            "bmi": serialized["bmi"],
            "weighted_family_score": serialized["weightedFamilyScore"],
            "overall_risk_band": serialized["overallRiskBand"],
            "average_percentage": serialized["averagePercentage"],
        }
        prediction_lookup = {item["key"]: item["percentage"] for item in serialized["predictions"]}
        for key, label in prediction_keys:
            row[f"{key}_percentage"] = prediction_lookup.get(key, "")
            row[f"{key}_label"] = label
        rows.append(row)

    return rows


def _csv_response(filename: str, rows: List[dict]) -> Response:
    """Create CSV response from rows."""
    output = StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["message"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    else:
        writer.writerow({"message": "No data available"})

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============= ENDPOINTS =============


@assessment_bp.post("/predict")
def predict():
    """Make prediction from assessment payload."""
    payload = request.get_json(silent=True) or {}

    try:
        user = _get_current_user(required=False)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    result = predict_assessment(payload)
    assessment_title = (
        str(payload.get("title", "")).strip()
        or f"Assessment {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    )

    stored_payload = {
        "v": _ASSESSMENT_STORE_VERSION,
        "form": payload,
        "respondentProbability": result["summary"]["averageProbability"],
        "lineageScenarioMultiplier": result.get("scenarioLineageMultiplier", 1.0),
    }
    assessment = Assessment(
        user_id=user.id if user else None,
        title=assessment_title,
        bmi=result["derivedMetrics"]["bmi"],
        weighted_family_score=result["derivedMetrics"]["weightedFamilyScore"],
        payload_json=json.dumps(stored_payload),
    )
    db.session.add(assessment)
    db.session.flush()

    for item in result["predictions"]:
        db.session.add(
            PredictionResult(
                assessment_id=assessment.id,
                target_key=item["key"],
                target_label=item["label"],
                probability=item["probability"],
                risk_band=item["riskBand"],
            )
        )

    db.session.commit()

    claims = verify_bearer_token()
    supabase_uid = claims.get("sub") if claims else None
    if supabase_uid:
        try:
            save_assessment_for_user(supabase_uid, payload, result)
        except Exception:
            current_app.logger.exception("Failed to save DESCEND assessment for Supabase user")

    saved = bool(user) or bool(supabase_uid)
    return jsonify({"assessmentId": assessment.id, "savedToHistory": saved, **result})


@assessment_bp.get("/history")
def history():
    """Get user's assessment history."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    search = request.args.get("search", "")
    start_date = request.args.get("startDate", "")
    end_date = request.args.get("endDate", "")
    assessments = _history_query(user, search, start_date, end_date)
    return jsonify({"items": [_serialize_assessment(item) for item in assessments]})


@assessment_bp.patch("/history/<int:assessment_id>")
def rename_history_item(assessment_id: int):
    """Update assessment title."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    assessment = Assessment.query.filter_by(id=assessment_id, user_id=user.id).first()
    if not assessment:
        return jsonify({"message": "Assessment record not found."}), 404

    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if len(title) < 3:
        return (
            jsonify({"message": "Assessment title must be at least 3 characters long."}),
            400,
        )

    assessment.title = title
    assessment.updated_at = _now()
    db.session.commit()
    return jsonify(
        {"message": "Assessment title updated.", "item": _serialize_assessment(assessment)}
    )


@assessment_bp.delete("/history/<int:assessment_id>")
def delete_history_item(assessment_id: int):
    """Delete assessment from history."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    assessment = Assessment.query.filter_by(id=assessment_id, user_id=user.id).first()
    if not assessment:
        return jsonify({"message": "Assessment record not found."}), 404

    db.session.delete(assessment)
    db.session.commit()
    return jsonify({"message": "Assessment deleted successfully."})


@assessment_bp.get("/history/export")
def export_history():
    """Export user's assessment history as CSV."""
    try:
        user = _get_current_user(required=True)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    search = request.args.get("search", "")
    start_date = request.args.get("startDate", "")
    end_date = request.args.get("endDate", "")
    assessments = _history_query(user, search, start_date, end_date)
    return _csv_response("assessment-history.csv", _history_export_rows(assessments))
