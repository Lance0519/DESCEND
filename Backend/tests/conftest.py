"""Shared pytest fixtures for T2DM backend tests."""

import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")

from descend import create_app
from descend.extensions import db as _db
from descend.models import User


@pytest.fixture(scope="session")
def app():
    """Create the Flask application for the entire test session."""
    application = create_app()
    application.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret-key-do-not-use-in-production",
        MAX_LOGIN_ATTEMPTS=5,
        LOGIN_LOCK_MINUTES=15,
        AUTH_TOKEN_MAX_AGE=3600,
        PASSWORD_RESET_MAX_AGE=3600,
        EXPOSE_RESET_TOKEN_PREVIEW=True,
        INITIAL_ADMIN_EMAIL="admin@test.com",
    )
    yield application


@pytest.fixture(autouse=True)
def db(app):
    """Create fresh database tables for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def sample_user(db, app):
    """Create a sample regular user and return (user, password)."""
    with app.app_context():
        password = "TestPassword1!safe"
        user = User(name="Test User", email="testuser@example.com", role="user")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user, password


@pytest.fixture()
def admin_user(db, app):
    """Create an admin user and return (user, password)."""
    with app.app_context():
        password = "AdminPassword1!safe"
        user = User(name="Admin User", email="admin@test.com", role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user, password


@pytest.fixture()
def auth_token(client, sample_user):
    """Get a valid auth token for the sample user."""
    _, password = sample_user
    response = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": password,
    })
    return response.get_json()["token"]


@pytest.fixture()
def admin_token(client, admin_user):
    """Get a valid auth token for the admin user."""
    _, password = admin_user
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": password,
    })
    return response.get_json()["token"]


@pytest.fixture()
def sample_assessment_payload():
    """Standard assessment payload for prediction tests."""
    return {
        "personalInfo": {
            "age": 35,
            "isFilipino": "yes",
            "sex": "male",
            "heightCm": 170,
            "weightKg": 80,
            "diagnosedT2dm": "no",
            "diagnosedT2dmConfirmationMethod": "not_applicable",
            "diagnosedHypertension": "no",
            "fatherHypertension": "no",
            "motherHypertension": "no",
        },
        "familyHistory": {
            "maternalGrandmother": "yes",
            "maternalGrandfather": "no",
            "paternalGrandmother": "unknown",
            "paternalGrandfather": "no",
            "mother": "yes",
            "father": "no",
            "motherGdmDuringIndexPregnancy": "no",
            "siblingsCount": 3,
            "siblingsDiabetesCount": 1,
            "siblingsHypertensionCount": 0,
            "paternalAuntsUnclesCount": 4,
            "paternalAuntsUnclesDiabetesCount": 0,
            "maternalAuntsUnclesCount": 3,
            "maternalAuntsUnclesDiabetesCount": 1,
            "physicalActivityScore": 2,
            "dietQualityScore": 2,
        },
    }
