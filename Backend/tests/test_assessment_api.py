"""Tests for the assessment and admin API endpoints."""

import pytest


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"


class TestPredictEndpoint:
    def test_predict_as_guest(self, client, sample_assessment_payload):
        response = client.post("/api/predict", json=sample_assessment_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert "predictions" in data
        assert len(data["predictions"]) == 4
        assert "summary" in data

    def test_predict_as_authenticated(self, client, auth_token, sample_assessment_payload):
        response = client.post("/api/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=sample_assessment_payload,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "assessmentId" in data
        assert data.get("savedToHistory") is True

    def test_predict_missing_body(self, client):
        response = client.post("/api/predict",
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code in (200, 400, 500)

    def test_predict_result_probabilities_valid(self, client, sample_assessment_payload):
        response = client.post("/api/predict", json=sample_assessment_payload)
        data = response.get_json()
        for pred in data["predictions"]:
            assert 0.0 <= pred["probability"] <= 1.0
            assert pred["riskBand"] in ("Low", "Moderate", "High")
            assert 0.0 <= pred["percentage"] <= 100.0


class TestHistoryEndpoints:
    def _create_assessment(self, client, token, payload):
        return client.post("/api/predict",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    def test_history_empty(self, client, auth_token):
        response = client.get("/api/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.get_json()["items"] == []

    def test_history_after_assessment(self, client, auth_token, sample_assessment_payload):
        self._create_assessment(client, auth_token, sample_assessment_payload)
        response = client.get("/api/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert len(items) == 1

    def test_history_rename(self, client, auth_token, sample_assessment_payload):
        create_response = self._create_assessment(client, auth_token, sample_assessment_payload)
        assessment_id = create_response.get_json()["assessmentId"]

        rename_response = client.patch(f"/api/history/{assessment_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"title": "My Renamed Assessment"},
        )
        assert rename_response.status_code == 200

    def test_history_delete(self, client, auth_token, sample_assessment_payload):
        create_response = self._create_assessment(client, auth_token, sample_assessment_payload)
        assessment_id = create_response.get_json()["assessmentId"]

        delete_response = client.delete(f"/api/history/{assessment_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert delete_response.status_code == 200

        history_response = client.get("/api/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert len(history_response.get_json()["items"]) == 0

    def test_history_requires_auth(self, client):
        response = client.get("/api/history")
        assert response.status_code == 401

    def test_history_export_csv(self, client, auth_token, sample_assessment_payload):
        self._create_assessment(client, auth_token, sample_assessment_payload)
        response = client.get("/api/history/export",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.content_type


class TestAdminEndpoints:
    def test_admin_overview(self, client, admin_token):
        response = client.get("/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "stats" in data
        assert "analytics" in data

    def test_admin_users_list(self, client, admin_token):
        response = client.get("/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "items" in response.get_json()

    def test_admin_requires_admin_role(self, client, auth_token):
        response = client.get("/api/admin/overview",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 403

    def test_admin_model_evaluation(self, client, admin_token):
        response = client.get("/api/admin/model/evaluation",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "source" in data
        assert "requiredColumns" in data

    def test_admin_change_user_role(self, client, admin_token, sample_user, app):
        with app.app_context():
            from descend.models import User
            user = User.query.filter_by(email="testuser@example.com").first()
            user_id = user.id

        response = client.patch(f"/api/admin/users/{user_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "admin"},
        )
        assert response.status_code == 200

    def test_admin_change_user_status(self, client, admin_token, sample_user, app):
        with app.app_context():
            from descend.models import User
            user = User.query.filter_by(email="testuser@example.com").first()
            user_id = user.id

        response = client.patch(f"/api/admin/users/{user_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"isActive": False},
        )
        assert response.status_code == 200

    def test_admin_reset_user_password(self, client, admin_token, sample_user, app):
        with app.app_context():
            from descend.models import User
            user = User.query.filter_by(email="testuser@example.com").first()
            user_id = user.id

        response = client.post(f"/api/admin/users/{user_id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "temporaryPassword" in data

    def test_admin_export_csv(self, client, admin_token):
        response = client.get("/api/admin/export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.content_type
