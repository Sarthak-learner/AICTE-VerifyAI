"""Tests for Prompt 06: Role-Based Access Control (RBAC).

Tests that:
- Viewer role has read-only access and is blocked with 403 on all action/mutation endpoints.
- Officer and Admin roles can perform operations (create apps, upload docs, validate, review).
- Public endpoints (health) remain accessible without credentials.
- Unauthenticated requests to protected endpoints receive 401 Unauthorized.
"""
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from tests.conftest import VALID_APPLICATION_PAYLOAD, make_pdf


def _make_user(db: Session, email: str, role: UserRole) -> User:
    user = User(
        email=email,
        full_name=f"User {email}",
        role=role,
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=user.email, role=user.role.value, user_id=user.id)


def _auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


class TestPublicAndUnauthenticatedAccess:
    def test_health_endpoint_is_public(self, unauthenticated_client: TestClient):
        """Health check endpoint requires no credentials."""
        resp = unauthenticated_client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_protected_endpoints_require_auth(self, unauthenticated_client: TestClient):
        """Endpoints without credentials return 401 Unauthorized."""
        assert unauthenticated_client.get("/api/v1/applications").status_code == 401
        assert unauthenticated_client.get("/api/v1/dashboard/stats").status_code == 401
        assert unauthenticated_client.get("/api/v1/rules").status_code == 401
        assert unauthenticated_client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD).status_code == 401


class TestViewerRoleLimitations:
    def test_viewer_can_read_endpoints(self, unauthenticated_client: TestClient, db: Session):
        """Viewer can access read-only endpoints (applications list, dashboard, rules)."""
        viewer = _make_user(db, "viewer_read@aicte.gov.in", UserRole.VIEWER)
        headers = _auth_header(viewer)

        # Dashboard
        resp = unauthenticated_client.get("/api/v1/dashboard/stats", headers=headers)
        assert resp.status_code == 200

        # Applications list
        resp = unauthenticated_client.get("/api/v1/applications", headers=headers)
        assert resp.status_code == 200

        # Rules list
        resp = unauthenticated_client.get("/api/v1/rules", headers=headers)
        assert resp.status_code == 200

    def test_viewer_cannot_create_application(self, unauthenticated_client: TestClient, db: Session):
        """Viewer receives 403 Forbidden when attempting to create an application."""
        viewer = _make_user(db, "viewer_no_create@aicte.gov.in", UserRole.VIEWER)
        headers = _auth_header(viewer)

        resp = unauthenticated_client.post(
            "/api/v1/applications",
            json=VALID_APPLICATION_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_viewer_cannot_upload_document(self, unauthenticated_client: TestClient, db: Session):
        """Viewer receives 403 Forbidden when attempting to upload a document."""
        officer = _make_user(db, "officer_setup@aicte.gov.in", UserRole.OFFICER)
        viewer = _make_user(db, "viewer_no_upload@aicte.gov.in", UserRole.VIEWER)

        # Officer creates application first
        app_resp = unauthenticated_client.post(
            "/api/v1/applications",
            json=VALID_APPLICATION_PAYLOAD,
            headers=_auth_header(officer),
        )
        app_id = app_resp.json()["id"]

        # Viewer attempts upload
        files = {"file": ("test.pdf", io.BytesIO(make_pdf()), "application/pdf")}
        upload_resp = unauthenticated_client.post(
            f"/api/v1/applications/{app_id}/documents",
            files=files,
            headers=_auth_header(viewer),
        )
        assert upload_resp.status_code == 403
        assert "Access denied" in upload_resp.json()["detail"]

    def test_viewer_cannot_trigger_validation(self, unauthenticated_client: TestClient, db: Session):
        """Viewer receives 403 Forbidden when attempting to trigger validation."""
        officer = _make_user(db, "officer_val@aicte.gov.in", UserRole.OFFICER)
        viewer = _make_user(db, "viewer_val@aicte.gov.in", UserRole.VIEWER)

        app_resp = unauthenticated_client.post(
            "/api/v1/applications",
            json=VALID_APPLICATION_PAYLOAD,
            headers=_auth_header(officer),
        )
        app_id = app_resp.json()["id"]

        resp = unauthenticated_client.post(
            f"/api/v1/applications/{app_id}/validate",
            headers=_auth_header(viewer),
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_viewer_cannot_review_findings(self, unauthenticated_client: TestClient, db: Session):
        """Viewer receives 403 Forbidden when attempting to review findings."""
        viewer = _make_user(db, "viewer_rev@aicte.gov.in", UserRole.VIEWER)
        headers = _auth_header(viewer)

        resp = unauthenticated_client.patch(
            "/api/v1/applications/fake-app-id/findings/fake-finding-id",
            json={"status": "resolved", "resolution_note": "Attempted viewer resolution"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_viewer_cannot_screen_authenticity(self, unauthenticated_client: TestClient, db: Session):
        """Viewer receives 403 Forbidden when attempting to run authenticity screening."""
        viewer = _make_user(db, "viewer_auth@aicte.gov.in", UserRole.VIEWER)
        headers = _auth_header(viewer)

        resp = unauthenticated_client.post(
            "/api/v1/applications/fake-app-id/authenticity-screen",
            headers=headers,
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]


class TestOfficerAndAdminCapabilities:
    def test_officer_can_create_and_upload(self, unauthenticated_client: TestClient, db: Session):
        """Officer can create applications and upload documents."""
        officer = _make_user(db, "officer_full@aicte.gov.in", UserRole.OFFICER)
        headers = _auth_header(officer)

        # Create
        resp = unauthenticated_client.post(
            "/api/v1/applications",
            json=VALID_APPLICATION_PAYLOAD,
            headers=headers,
        )
        assert resp.status_code == 201
        app_id = resp.json()["id"]

        # Upload
        files = {"file": ("doc.pdf", io.BytesIO(make_pdf()), "application/pdf")}
        upload_resp = unauthenticated_client.post(
            f"/api/v1/applications/{app_id}/documents",
            files=files,
            headers=headers,
        )
        assert upload_resp.status_code == 201
        assert upload_resp.json()["document"]["original_filename"] == "doc.pdf"

    def test_officer_can_run_validation_and_screening(self, unauthenticated_client: TestClient, db: Session):
        """Officer can trigger validation and authenticity screening."""
        officer = _make_user(db, "officer_ops@aicte.gov.in", UserRole.OFFICER)
        headers = _auth_header(officer)

        app_id = unauthenticated_client.post(
            "/api/v1/applications",
            json=VALID_APPLICATION_PAYLOAD,
            headers=headers,
        ).json()["id"]

        val_resp = unauthenticated_client.post(
            f"/api/v1/applications/{app_id}/validate",
            headers=headers,
        )
        assert val_resp.status_code == 200

        screen_resp = unauthenticated_client.post(
            f"/api/v1/applications/{app_id}/authenticity-screen",
            headers=headers,
        )
        assert screen_resp.status_code == 200
