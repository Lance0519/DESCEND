"""DESCEND profile + history endpoints (Supabase JWT)."""

from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..supabase_auth import optional_supabase_user, require_supabase_user

profile_bp = Blueprint("profile", __name__)


class DescendProfile(db.Model):
    __tablename__ = "descend_profiles"

    id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    preferred_lang = db.Column(db.String(8), default="tl")
    sex = db.Column(db.String(16))
    age = db.Column(db.Integer)
    avatar_url = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DescendAssessmentSave(db.Model):
    __tablename__ = "descend_assessment_saves"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), index=True, nullable=False)
    percentage = db.Column(db.Float)
    risk_band = db.Column(db.String(32))
    result_json = db.Column(db.Text)
    answers_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@profile_bp.get("/profile")
@require_supabase_user
def get_profile():
    row = DescendProfile.query.get(g.supabase_user_id)
    if not row:
        row = DescendProfile(
            id=g.supabase_user_id,
            email=g.supabase_email,
            display_name="",
            preferred_lang="tl",
        )
        db.session.add(row)
        db.session.commit()
    return jsonify(
        {
            "id": row.id,
            "email": row.email or g.supabase_email,
            "display_name": row.display_name,
            "preferred_lang": row.preferred_lang,
            "sex": row.sex,
            "age": row.age,
            "avatar_url": row.avatar_url,
        }
    )


@profile_bp.patch("/profile")
@require_supabase_user
def patch_profile():
    body = request.get_json(silent=True) or {}
    row = DescendProfile.query.get(g.supabase_user_id)
    if not row:
        row = DescendProfile(id=g.supabase_user_id, email=g.supabase_email)
        db.session.add(row)
    if "display_name" in body:
        row.display_name = str(body.get("display_name") or "")[:255]
    if "preferred_lang" in body:
        row.preferred_lang = str(body.get("preferred_lang") or "tl")[:8]
    if "sex" in body:
        row.sex = str(body.get("sex") or "")[:16] or None
    if "age" in body:
        try:
            row.age = int(body["age"]) if body["age"] is not None else None
        except (TypeError, ValueError):
            row.age = None
    if "avatar_url" in body:
        row.avatar_url = body.get("avatar_url")
    db.session.commit()
    return jsonify({"ok": True})


@profile_bp.get("/profile/history")
@require_supabase_user
def get_history():
    rows = (
        DescendAssessmentSave.query.filter_by(user_id=g.supabase_user_id)
        .order_by(DescendAssessmentSave.created_at.desc())
        .limit(50)
        .all()
    )
    items = []
    for row in rows:
        result = {}
        try:
            result = json.loads(row.result_json or "{}")
        except json.JSONDecodeError:
            result = {}
        items.append(
            {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "percentage": row.percentage,
                "risk_band": row.risk_band,
                "result": result,
            }
        )
    return jsonify({"items": items})


def save_assessment_for_user(user_id: str, payload: dict, result: dict) -> None:
    if not user_id:
        return
    summary = result.get("summary") or {}
    soft = result.get("softAdjustment") or {}
    row = DescendAssessmentSave(
        user_id=user_id,
        percentage=summary.get("averagePercentage"),
        risk_band=summary.get("overallRiskBand"),
        result_json=json.dumps(
            {
                "percentage": summary.get("averagePercentage"),
                "riskBand": summary.get("overallRiskBand"),
                "softAdjustment": soft,
                "scenarioProbabilities": result.get("scenarioProbabilities"),
                "predictions": result.get("predictions"),
            }
        ),
        answers_json=json.dumps(payload),
    )
    db.session.add(row)
    db.session.commit()


@profile_bp.post("/profile/history/save")
@optional_supabase_user
def save_history_explicit():
    if not g.supabase_user_id:
        return jsonify({"saved": False}), 200
    body = request.get_json(silent=True) or {}
    save_assessment_for_user(
        g.supabase_user_id,
        body.get("answers") or {},
        body.get("result") or {},
    )
    return jsonify({"saved": True})
