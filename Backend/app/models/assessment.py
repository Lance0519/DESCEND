"""Assessment and prediction result models."""

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
    bmi = db.Column(db.Float, nullable=False)
    weighted_family_score = db.Column(db.Float, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)

    # Relationship to predictions
    predictions = db.relationship(
        "PredictionResult",
        backref="assessment",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self) -> str:
        return f"<Assessment {self.id} ({self.title})>"


class PredictionResult(db.Model):
    """Individual prediction result for a target (child/grandchild scenario)."""
    
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
