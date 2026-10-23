"""Tests for Prompt 06: Authentication and User Management.

Tests login, token generation, profile retrieval, user seeding, and admin user CRUD.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.services.user_service import create_user, seed_default_users
from app.schemas.user import UserCreate


def _create_db_user(db: Session, email: str, role: UserRole, password: str = "Password@123", is_active: bool = True) -> User:
    user = User(
        email=email,
        full_name=f"User {email}",
        role=role,
        hashed_password=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestAuthenticationEndpoints:
    def test_login_successful(self, unauthenticated_client: TestClient, db: Session):
        """Valid email and password should return 200 with JWT access token."""
        _create_db_user(db, "officer1@aicte.gov.in", UserRole.OFFICER, "ValidPass123")

        resp = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "officer1@aicte.gov.in", "password": "ValidPass123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "officer1@aicte.gov.in"
        assert body["user"]["role"] == "officer"

    def test_login_invalid_password_returns_401(self, unauthenticated_client: TestClient, db: Session):
        """Invalid password should return 401 Unauthorized."""
        _create_db_user(db, "officer2@aicte.gov.in", UserRole.OFFICER, "CorrectPass")

        resp = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "officer2@aicte.gov.in", "password": "WrongPassword"},
        )
        assert resp.status_code == 401
        assert "Incorrect email or password" in resp.json()["detail"]

    def test_login_nonexistent_user_returns_401(self, unauthenticated_client: TestClient):
        """Non-existent user should return 401 Unauthorized."""
        resp = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@aicte.gov.in", "password": "Password123"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user_returns_403(self, unauthenticated_client: TestClient, db: Session):
        """Inactive user account should return 403 Forbidden."""
        _create_db_user(db, "disabled@aicte.gov.in", UserRole.OFFICER, "Pass123", is_active=False)

        resp = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@aicte.gov.in", "password": "Pass123"},
        )
        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"].lower()

    def test_get_me_with_valid_token(self, unauthenticated_client: TestClient, db: Session):
        """GET /auth/me with valid Bearer token returns current user profile."""
        user = _create_db_user(db, "officer3@aicte.gov.in", UserRole.OFFICER)
        token = create_access_token(subject=user.email, role=user.role.value, user_id=user.id)

        resp = unauthenticated_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "officer3@aicte.gov.in"
        assert body["role"] == "officer"

    def test_get_me_without_token_returns_401(self, unauthenticated_client: TestClient):
        """GET /auth/me without token returns 401 Unauthorized."""
        resp = unauthenticated_client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_me_with_invalid_token_returns_401(self, unauthenticated_client: TestClient):
        """GET /auth/me with garbage token returns 401 Unauthorized."""
        resp = unauthenticated_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.garbage.token"},
        )
        assert resp.status_code == 401

    def test_seed_demo_accounts(self, unauthenticated_client: TestClient, db: Session):
        """POST /auth/seed should populate the default demo accounts."""
        resp = unauthenticated_client.post("/api/v1/auth/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["accounts"]) == 3

        # Verify default officer can now log in
        login_resp = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "officer@aicte.gov.in", "password": "Officer@123"},
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["user"]["role"] == "officer"


class TestAdminUserManagement:
    def test_admin_can_list_users(self, unauthenticated_client: TestClient, db: Session):
        """Admin can list all system users."""
        admin = _create_db_user(db, "admin1@aicte.gov.in", UserRole.ADMIN)
        token = create_access_token(subject=admin.email, role=admin.role.value, user_id=admin.id)

        resp = unauthenticated_client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_officer_cannot_list_users(self, unauthenticated_client: TestClient, db: Session):
        """Non-admin user (officer) receives 403 Forbidden when listing users."""
        officer = _create_db_user(db, "officer_denied@aicte.gov.in", UserRole.OFFICER)
        token = create_access_token(subject=officer.email, role=officer.role.value, user_id=officer.id)

        resp = unauthenticated_client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_admin_can_create_user(self, unauthenticated_client: TestClient, db: Session):
        """Admin can create a new user account."""
        admin = _create_db_user(db, "admin2@aicte.gov.in", UserRole.ADMIN)
        token = create_access_token(subject=admin.email, role=admin.role.value, user_id=admin.id)

        new_user_payload = {
            "email": "new_officer@aicte.gov.in",
            "full_name": "New Verification Officer",
            "role": "officer",
            "password": "SecurePassword123",
            "is_active": True,
        }
        resp = unauthenticated_client.post(
            "/api/v1/auth/users",
            json=new_user_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "new_officer@aicte.gov.in"
        assert resp.json()["role"] == "officer"
