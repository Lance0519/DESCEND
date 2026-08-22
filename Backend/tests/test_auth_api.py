"""Tests for authentication API endpoints."""

import pytest


class TestRegister:
    def test_register_first_account_becomes_admin(self, client):
        response = client.post("/api/auth/register", json={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["role"] == "admin"

    def test_register_second_account_becomes_user(self, client):
        client.post("/api/auth/register", json={
            "name": "First Admin",
            "email": "admin1@example.com",
            "password": "SecurePass123!abc",
        })
        response = client.post("/api/auth/register", json={
            "name": "Second User",
            "email": "user2@example.com",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 201
        assert response.get_json()["user"]["role"] == "user"

    def test_register_admin_bootstrap(self, client, db, app):
        with app.app_context():
            from app.models import User

            user = User(name="Existing User", email="existing@example.com", role="user")
            user.set_password("SecurePass123!abc")
            db.session.add(user)
            db.session.commit()

        response = client.post("/api/auth/register", json={
            "name": "Admin Bootstrap",
            "email": "admin@test.com",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 201
        assert response.get_json()["user"]["role"] == "admin"

    def test_register_duplicate_email(self, client, sample_user):
        response = client.post("/api/auth/register", json={
            "name": "Dup User",
            "email": "testuser@example.com",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Weak Pass",
            "email": "weakpass@example.com",
            "password": "short",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "issues" in data

    def test_register_invalid_email(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 400

    def test_register_short_name(self, client):
        response = client.post("/api/auth/register", json={
            "name": "X",
            "email": "shortname@example.com",
            "password": "SecurePass123!abc",
        })
        assert response.status_code == 400

    def test_register_password_contains_email(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "myemail@example.com",
            "password": "myemailSecure123!",
        })
        assert response.status_code == 400


class TestLogin:
    def test_login_success(self, client, sample_user):
        _, password = sample_user
        response = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": password,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["user"]["email"] == "testuser@example.com"

    def test_login_wrong_password(self, client, sample_user):
        response = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "SomePassword123!",
        })
        assert response.status_code == 401

    def test_login_lockout_after_failures(self, client, sample_user):
        for _ in range(5):
            client.post("/api/auth/login", json={
                "email": "testuser@example.com",
                "password": "WrongPassword123!",
            })
        response = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": "WrongPassword123!",
        })
        assert response.status_code == 423

    def test_login_disabled_user(self, client, db, sample_user, app):
        user, password = sample_user
        with app.app_context():
            from app.models import User
            u = User.query.filter_by(email="testuser@example.com").first()
            u.is_active = False
            db.session.commit()
        response = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": password,
        })
        assert response.status_code == 403


class TestAuthMe:
    def test_me_authenticated(self, client, auth_token):
        response = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {auth_token}",
        })
        assert response.status_code == 200
        assert response.get_json()["user"]["email"] == "testuser@example.com"

    def test_me_no_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid-token-here",
        })
        assert response.status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, auth_token, sample_user):
        _, old_password = sample_user
        response = client.post("/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "currentPassword": old_password,
                "newPassword": "NewSecurePass456!xyz",
            },
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client, auth_token):
        response = client.post("/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "currentPassword": "WrongCurrent123!",
                "newPassword": "NewSecurePass456!xyz",
            },
        )
        assert response.status_code == 400

    def test_change_password_same_as_current(self, client, auth_token, sample_user):
        _, old_password = sample_user
        response = client.post("/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "currentPassword": old_password,
                "newPassword": old_password,
            },
        )
        assert response.status_code == 400


class TestForgotAndResetPassword:
    def test_forgot_password_existing_email(self, client, sample_user):
        response = client.post("/api/auth/forgot-password", json={
            "email": "testuser@example.com",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "resetTokenPreview" in data

    def test_forgot_password_nonexistent_email(self, client):
        response = client.post("/api/auth/forgot-password", json={
            "email": "nobody@example.com",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "resetTokenPreview" not in data

    def test_full_reset_flow(self, client, sample_user):
        forgot_response = client.post("/api/auth/forgot-password", json={
            "email": "testuser@example.com",
        })
        token = forgot_response.get_json()["resetTokenPreview"]

        reset_response = client.post("/api/auth/reset-password", json={
            "token": token,
            "newPassword": "ResetNewPass789!xyz",
        })
        assert reset_response.status_code == 200

        login_response = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": "ResetNewPass789!xyz",
        })
        assert login_response.status_code == 200

    def test_reset_with_invalid_token(self, client):
        response = client.post("/api/auth/reset-password", json={
            "token": "invalid-token",
            "newPassword": "NewSecurePass123!abc",
        })
        assert response.status_code == 400
