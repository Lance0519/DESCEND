"""Assessment, prediction, and typed patient survey record models."""

from datetime import datetime

from ..extensions import db


class Assessment(db.Model):
    """Assessment record storing user input and metadata."""

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(160), nullable=False, default="Assessment Record")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    bmi = db.Column(db.Float, nullable=False, default=0.0)
    weighted_family_score = db.Column(db.Float, nullable=False, default=0.0)
    payload_json = db.Column(db.Text, nullable=False)

    # Strict diagnosis profile fields
    diagnosed_t2dm = db.Column(db.Boolean, nullable=False, default=False)
    age_of_onset = db.Column(db.Integer, nullable=True)

    # Numerical survey answers / calculated metrics (typed for future analytics)
    age = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    hypertension = db.Column(db.Boolean, nullable=True)
    physical_activity_score = db.Column(db.Integer, nullable=True)
    diet_quality_score = db.Column(db.Integer, nullable=True)
    fasting_glucose_mg_dl = db.Column(db.Float, nullable=True)
    hba1c_percent = db.Column(db.Float, nullable=True)
    risk_percentage = db.Column(db.Float, nullable=True)
    risk_probability = db.Column(db.Float, nullable=True)
    risk_band = db.Column(db.String(20), nullable=True)
    feature_vector_json = db.Column(db.Text, nullable=True)

    predictions = db.relationship(
        "PredictionResult",
        backref="assessment",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self) -> str:
        return f"<Assessment {self.id} diagnosed={self.diagnosed_t2dm}>"


class PredictionResult(db.Model):
    """Individual prediction result for a target (child scenario)."""

    __tablename__ = "prediction_results"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id"), nullable=False
    )
    target_key = db.Column(db.String(50), nullable=False)
    target_label = db.Column(db.String(120), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    risk_band = db.Column(db.String(20), nullable=False)

    def __repr__(self) -> str:
        return f"<PredictionResult {self.target_label}: {self.probability:.2%}>"


class PatientSurveyRecord(db.Model):
    """
    Typed store for two patient profiles:
    - diagnosed_t2dm=True  → management path (age_of_onset required; no ExtraTrees score)
    - diagnosed_t2dm=False → predictive path (survey metrics + feature vector + risk %)
    """

    __tablename__ = "patient_survey_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    supabase_user_id = db.Column(db.String(64), nullable=True, index=True)

    diagnosed_t2dm = db.Column(db.Boolean, nullable=False)
    age_of_onset = db.Column(db.Integer, nullable=True)

    age = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    hypertension = db.Column(db.Boolean, nullable=True)
    physical_activity_score = db.Column(db.Integer, nullable=True)
    diet_quality_score = db.Column(db.Integer, nullable=True)
    fasting_glucose_mg_dl = db.Column(db.Float, nullable=True)
    hba1c_percent = db.Column(db.Float, nullable=True)
    maternal_aunts_uncles_diabetes_count = db.Column(db.Integer, nullable=True, default=0)
    paternal_aunts_uncles_diabetes_count = db.Column(db.Integer, nullable=True, default=0)
    siblings_diabetes_count = db.Column(db.Integer, nullable=True, default=0)

    bmi = db.Column(db.Float, nullable=True)
    weighted_family_score = db.Column(db.Float, nullable=True)
    risk_percentage = db.Column(db.Float, nullable=True)
    risk_probability = db.Column(db.Float, nullable=True)
    risk_band = db.Column(db.String(20), nullable=True)
    feature_vector_json = db.Column(db.Text, nullable=True)
    answers_json = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PatientSurveyRecord {self.id} diagnosed={self.diagnosed_t2dm}>"
