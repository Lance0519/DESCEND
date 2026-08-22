"""Estimation workflow: diagnosed → management; undiagnosed → ExtraTrees feature array + score."""

from __future__ import annotations

import json
from typing import Any

from flask import current_app

from ..extensions import db
from ..ml.feature_builder import build_base_features
from ..ml.modeling import FEATURE_COLUMNS
from ..ml.predictor import predict_assessment, risk_band_for_probability
from ..models import Assessment, PatientSurveyRecord, PredictionResult
from ..supabase_auth import verify_bearer_token
from .profile import save_assessment_for_user


def _as_bool_diagnosed(personal: dict) -> bool:
    raw = personal.get("diagnosedT2dm", personal.get("diagnosed_t2dm"))
    if isinstance(raw, bool):
        return raw
    return str(raw or "").strip().lower() in {"yes", "true", "1"}


def _as_optional_int(value: Any, *, lo: int = 1, hi: int = 120) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    if n < lo or n > hi:
        return None
    return n


def _as_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_bool_yes(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"yes", "true", "1"}:
        return True
    if s in {"no", "false", "0"}:
        return False
    return None


def format_feature_array(features: dict[str, float]) -> list[float]:
    """Normalized numerical feature row for ExtraTrees (column order = FEATURE_COLUMNS)."""
    return [float(features.get(col, 0.0)) for col in FEATURE_COLUMNS]


def extract_typed_metrics(payload: dict) -> dict[str, Any]:
    personal = payload.get("personalInfo") or {}
    family = payload.get("familyHistory") or {}
    labs = payload.get("labs") or {}
    ages = payload.get("diagnosisAges") or {}

    return {
        "diagnosed": _as_bool_diagnosed(personal),
        "age_of_onset": _as_optional_int(ages.get("self") or personal.get("ageAtDiagnosis")),
        "age": _as_optional_int(personal.get("age"), lo=1, hi=120),
        "height_cm": _as_optional_float(personal.get("heightCm")),
        "weight_kg": _as_optional_float(personal.get("weightKg")),
        "hypertension": _as_optional_bool_yes(
            personal.get("diagnosedHypertension") or personal.get("hypertension")
        ),
        "physical_activity_score": _as_optional_int(
            family.get("physicalActivityScore"), lo=1, hi=4
        ),
        "diet_quality_score": _as_optional_int(family.get("dietQualityScore"), lo=1, hi=3),
        "fasting_glucose_mg_dl": _as_optional_float(labs.get("fastingGlucoseMgDl")),
        "hba1c_percent": _as_optional_float(labs.get("hba1cPercent")),
        "maternal_aunts_uncles_diabetes_count": _as_optional_int(
            family.get("maternalAuntsUnclesDiabetesCount"), lo=0, hi=50
        )
        or 0,
        "paternal_aunts_uncles_diabetes_count": _as_optional_int(
            family.get("paternalAuntsUnclesDiabetesCount"), lo=0, hi=50
        )
        or 0,
        "siblings_diabetes_count": _as_optional_int(
            family.get("siblingsDiabetesCount"), lo=0, hi=50
        )
        or 0,
    }


def management_response(*, age_of_onset: int | None, record_id: int | None) -> dict:
    return {
        "path": "management",
        "diagnosed": True,
        "ageOfOnset": age_of_onset,
        "recordId": record_id,
        "message": (
            "Existing Type 2 diabetes diagnosis — predictive ExtraTrees scoring is not applied. "
            "Use lifestyle management guidance instead."
        ),
        "summary": None,
        "predictions": [],
        "featureVector": None,
        "featureColumns": list(FEATURE_COLUMNS),
    }


def persist_survey_record(
    *,
    payload: dict,
    metrics: dict[str, Any],
    result: dict | None,
    feature_vector: list[float] | None,
    flask_user_id: int | None,
    supabase_uid: str | None,
) -> PatientSurveyRecord:
    derived = (result or {}).get("derivedMetrics") or {}
    summary = (result or {}).get("summary") or {}

    record = PatientSurveyRecord(
        user_id=flask_user_id,
        supabase_user_id=supabase_uid,
        diagnosed_t2dm=bool(metrics["diagnosed"]),
        age_of_onset=metrics["age_of_onset"],
        age=metrics["age"],
        height_cm=metrics["height_cm"],
        weight_kg=metrics["weight_kg"],
        hypertension=metrics["hypertension"],
        physical_activity_score=metrics["physical_activity_score"],
        diet_quality_score=metrics["diet_quality_score"],
        fasting_glucose_mg_dl=metrics["fasting_glucose_mg_dl"],
        hba1c_percent=metrics["hba1c_percent"],
        maternal_aunts_uncles_diabetes_count=metrics["maternal_aunts_uncles_diabetes_count"],
        paternal_aunts_uncles_diabetes_count=metrics["paternal_aunts_uncles_diabetes_count"],
        siblings_diabetes_count=metrics["siblings_diabetes_count"],
        bmi=_as_optional_float(derived.get("bmi")),
        weighted_family_score=_as_optional_float(derived.get("weightedFamilyScore")),
        risk_percentage=_as_optional_float(summary.get("averagePercentage")),
        risk_probability=_as_optional_float(summary.get("averageProbability")),
        risk_band=summary.get("overallRiskBand"),
        feature_vector_json=json.dumps(feature_vector) if feature_vector is not None else None,
        answers_json=json.dumps(payload),
        result_json=json.dumps(result) if result is not None else None,
    )
    db.session.add(record)
    return record


def persist_assessment_row(
    *,
    payload: dict,
    metrics: dict[str, Any],
    result: dict | None,
    feature_vector: list[float] | None,
    flask_user_id: int | None,
    title: str,
) -> Assessment:
    derived = (result or {}).get("derivedMetrics") or {}
    summary = (result or {}).get("summary") or {}
    bmi = float(derived.get("bmi") or 0.0)
    wfs = float(derived.get("weightedFamilyScore") or 0.0)

    stored_payload = {
        "v": 2,
        "form": payload,
        "path": "management" if metrics["diagnosed"] else "predictive",
        "respondentProbability": summary.get("averageProbability"),
        "lineageScenarioMultiplier": (result or {}).get("scenarioLineageMultiplier", 1.0),
    }

    assessment = Assessment(
        user_id=flask_user_id,
        title=title,
        bmi=bmi,
        weighted_family_score=wfs,
        payload_json=json.dumps(stored_payload),
        diagnosed_t2dm=bool(metrics["diagnosed"]),
        age_of_onset=metrics["age_of_onset"],
        age=metrics["age"],
        height_cm=metrics["height_cm"],
        weight_kg=metrics["weight_kg"],
        hypertension=metrics["hypertension"],
        physical_activity_score=metrics["physical_activity_score"],
        diet_quality_score=metrics["diet_quality_score"],
        fasting_glucose_mg_dl=metrics["fasting_glucose_mg_dl"],
        hba1c_percent=metrics["hba1c_percent"],
        risk_percentage=_as_optional_float(summary.get("averagePercentage")),
        risk_probability=_as_optional_float(summary.get("averageProbability")),
        risk_band=summary.get("overallRiskBand"),
        feature_vector_json=json.dumps(feature_vector) if feature_vector is not None else None,
    )
    db.session.add(assessment)
    db.session.flush()

    if result:
        for item in result.get("predictions") or []:
            db.session.add(
                PredictionResult(
                    assessment_id=assessment.id,
                    target_key=item["key"],
                    target_label=item["label"],
                    probability=item["probability"],
                    risk_band=item.get("riskBand")
                    or risk_band_for_probability(float(item["probability"])),
                )
            )
    return assessment


def run_estimation(payload: dict, *, flask_user=None) -> dict:
    """
    Dedicated estimation workflow:
    - diagnosed → management payload (no ExtraTrees)
    - undiagnosed → feature array + ExtraTrees positive-class probability × 100
    """
    metrics = extract_typed_metrics(payload)
    claims = verify_bearer_token()
    supabase_uid = claims.get("sub") if claims else None
    flask_user_id = flask_user.id if flask_user else None

    title = (
        str(payload.get("title", "")).strip()
        or ("Diagnosed management profile" if metrics["diagnosed"] else "Risk estimation")
    )

    if metrics["diagnosed"]:
        if metrics["age_of_onset"] is None:
            raise ValueError("age_of_onset is required when diagnosed_t2dm is true")

        record = persist_survey_record(
            payload=payload,
            metrics=metrics,
            result=None,
            feature_vector=None,
            flask_user_id=flask_user_id,
            supabase_uid=supabase_uid,
        )
        assessment = persist_assessment_row(
            payload=payload,
            metrics=metrics,
            result=None,
            feature_vector=None,
            flask_user_id=flask_user_id,
            title=title,
        )
        db.session.commit()
        return {
            **management_response(age_of_onset=metrics["age_of_onset"], record_id=record.id),
            "assessmentId": assessment.id,
            "savedToHistory": bool(flask_user_id or supabase_uid),
        }

    # Undiagnosed: build features → ExtraTrees → percentage
    base_features, _derived = build_base_features(payload)
    feature_vector = format_feature_array(base_features)
    result = predict_assessment(payload)
    # Ensure percentage is model probability × 100 (already done in predictor; assert shape)
    model_pct = result.get("summary", {}).get("modelAveragePercentage")
    if model_pct is None and result.get("summary", {}).get("modelAverageProbability") is not None:
        result["summary"]["modelAveragePercentage"] = round(
            float(result["summary"]["modelAverageProbability"]) * 100, 1
        )

    record = persist_survey_record(
        payload=payload,
        metrics=metrics,
        result=result,
        feature_vector=feature_vector,
        flask_user_id=flask_user_id,
        supabase_uid=supabase_uid,
    )
    assessment = persist_assessment_row(
        payload=payload,
        metrics=metrics,
        result=result,
        feature_vector=feature_vector,
        flask_user_id=flask_user_id,
        title=title,
    )

    if supabase_uid:
        try:
            save_assessment_for_user(supabase_uid, payload, result)
        except Exception:
            current_app.logger.exception("Failed to save DESCEND assessment for Supabase user")

    db.session.commit()

    return {
        "path": "predictive",
        "diagnosed": False,
        "ageOfOnset": None,
        "recordId": record.id,
        "assessmentId": assessment.id,
        "savedToHistory": bool(flask_user_id or supabase_uid),
        "featureVector": feature_vector,
        "featureColumns": list(FEATURE_COLUMNS),
        **result,
    }
