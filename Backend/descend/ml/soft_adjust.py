"""Soft-adjustment layer for lifestyle, optional blood labs, and early-onset ages.

Applied after ExtraTrees + structural blend. See docs/RISK_SCORING.md.
"""

from __future__ import annotations


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lifestyle_deltas(lifestyle: dict | None) -> tuple[float, list[dict]]:
    if not lifestyle:
        return 0.0, []

    contributions: list[dict] = []
    total = 0.0

    freq = str(lifestyle.get("exerciseFrequency") or "").lower()
    level = str(lifestyle.get("physicalActivityLevel") or "").lower()
    duration = str(lifestyle.get("exerciseDurationMin") or "").lower()

    high_exercise = freq in {"5_plus_week", "5+"} and duration in {"30_60", "60_plus"}
    rare_short = (
        freq in {"rarely", "rare", ""}
        or level == "low"
        or duration in {"under_15", "<15"}
    )

    if high_exercise:
        total += -0.03
        contributions.append(
            {"id": "activity", "label": "activity", "delta": -0.03, "group": "lifestyle"}
        )
    elif rare_short and (freq or level or duration):
        total += 0.04
        contributions.append(
            {"id": "activity", "label": "activity", "delta": 0.04, "group": "lifestyle"}
        )

    sugary = str(lifestyle.get("sugaryDrinkFrequency") or "").lower()
    if sugary == "daily":
        total += 0.035
        contributions.append(
            {"id": "sugary", "label": "sugary", "delta": 0.035, "group": "lifestyle"}
        )
    elif sugary in {"several_week", "several"}:
        total += 0.02
        contributions.append(
            {"id": "sugary", "label": "sugary", "delta": 0.02, "group": "lifestyle"}
        )

    fast = str(lifestyle.get("fastFoodFrequency") or "").lower()
    if fast == "daily":
        total += 0.03
        contributions.append(
            {"id": "fastFood", "label": "fastFood", "delta": 0.03, "group": "lifestyle"}
        )
    elif fast in {"several_week", "several"}:
        total += 0.015
        contributions.append(
            {"id": "fastFood", "label": "fastFood", "delta": 0.015, "group": "lifestyle"}
        )

    smoking = str(lifestyle.get("smokingStatus") or "").lower()
    if smoking == "current":
        total += 0.04
        contributions.append(
            {"id": "smoking", "label": "smoking", "delta": 0.04, "group": "lifestyle"}
        )
    elif smoking == "former":
        total += 0.015
        contributions.append(
            {"id": "smoking", "label": "smoking", "delta": 0.015, "group": "lifestyle"}
        )

    alcohol = str(lifestyle.get("alcoholConsumption") or "").lower()
    if alcohol == "regular":
        total += 0.025
        contributions.append(
            {"id": "alcohol", "label": "alcohol", "delta": 0.025, "group": "lifestyle"}
        )

    sleep = str(lifestyle.get("sleepDurationHours") or "").lower()
    if sleep in {"under_6", "<6"}:
        total += 0.03
        contributions.append(
            {"id": "sleep", "label": "sleep", "delta": 0.03, "group": "lifestyle"}
        )
    elif sleep in {"7_8", "7-8"}:
        total += -0.01
        contributions.append(
            {"id": "sleep", "label": "sleep", "delta": -0.01, "group": "lifestyle"}
        )

    total = _clamp(total, -0.12, 0.12)
    return total, contributions


def _blood_deltas(labs: dict | None) -> tuple[float, list[dict]]:
    if not labs:
        return 0.0, []

    contributions: list[dict] = []
    total = 0.0

    glucose = labs.get("fastingGlucoseMgDl")
    if glucose is not None:
        try:
            g = float(glucose)
            if g < 100:
                d = -0.01
            elif g < 126:
                d = 0.04
            else:
                d = 0.07
            total += d
            contributions.append(
                {"id": "glucose", "label": "glucose", "delta": d, "group": "blood"}
            )
        except (TypeError, ValueError):
            pass

    hba1c = labs.get("hba1cPercent")
    if hba1c is not None:
        try:
            h = float(hba1c)
            if h < 5.7:
                d = -0.01
            elif h < 6.5:
                d = 0.045
            else:
                d = 0.08
            total += d
            contributions.append(
                {"id": "hba1c", "label": "hba1c", "delta": d, "group": "blood"}
            )
        except (TypeError, ValueError):
            pass

    total = _clamp(total, -0.1, 0.1)
    return total, contributions


def _early_onset_delta(diagnosis_ages: dict | None, family_history: dict | None) -> tuple[float, list[dict]]:
    if not diagnosis_ages:
        return 0.0, []

    first_degree_ages: list[float] = []
    for key in ("father", "mother", "sibling"):
        age_val = diagnosis_ages.get(key)
        if age_val is None:
            continue
        try:
            first_degree_ages.append(float(age_val))
        except (TypeError, ValueError):
            continue

    total = 0.0
    for age in sorted(first_degree_ages)[:2]:
        if age < 40:
            total += 0.025
        elif age <= 50:
            total += 0.015
        else:
            total += 0.005

    gp_keys = (
        "maternalGrandfather",
        "maternalGrandmother",
        "paternalGrandfather",
        "paternalGrandmother",
    )
    gp_ages: list[float] = []
    for key in gp_keys:
        age_val = diagnosis_ages.get(key)
        if age_val is None:
            continue
        try:
            age = float(age_val)
        except (TypeError, ValueError):
            continue
        if age < 50:
            gp_ages.append(age)

    for _ in gp_ages[:2]:
        total += 0.01

    total = _clamp(total, 0.0, 0.06)
    contributions: list[dict] = []
    if total > 0:
        contributions.append(
            {
                "id": "earlyOnset",
                "label": "earlyOnset",
                "delta": round(total, 4),
                "group": "earlyOnset",
            }
        )
    return total, contributions


def apply_soft_adjustment(
    probability: float,
    payload: dict,
) -> tuple[float, dict]:
    """Return adjusted probability and softAdjustment breakdown."""
    lifestyle_delta, lifestyle_contrib = _lifestyle_deltas(payload.get("lifestyle"))
    blood_delta, blood_contrib = _blood_deltas(payload.get("labs"))
    early_delta, early_contrib = _early_onset_delta(
        payload.get("diagnosisAges"),
        payload.get("familyHistory"),
    )

    net = lifestyle_delta + blood_delta + early_delta
    adjusted = _clamp(float(probability) + net, 0.02, 0.98)

    contributions = [
        {
            "id": "base",
            "label": "base",
            "delta": round(float(probability), 4),
            "group": "base",
        },
        *lifestyle_contrib,
        *blood_contrib,
        *early_contrib,
    ]

    soft = {
        "lifestyle": round(lifestyle_delta, 4),
        "blood": round(blood_delta, 4),
        "earlyOnset": round(early_delta, 4),
        "base": round(float(probability), 4),
        "net": round(net, 4),
        "contributions": contributions,
    }
    return adjusted, soft
