"""Tests for application creation, listing, and detail endpoints."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import VALID_APPLICATION_PAYLOAD


# ── Application creation ──────────────────────────────────────────────────────

class TestCreateApplication:
    def test_creates_successfully(self, client: TestClient):
        """A valid payload produces a 201 response with DRAFT status."""
        resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "draft"
        assert body["institution_name"] == VALID_APPLICATION_PAYLOAD["institution_name"]
        assert body["academic_year"] == "2025-26"
        assert body["application_category"] == "new_programme"
        assert body["programme_type"] == "BE_BTech"
        assert "id" in body
        assert body["reference_number"].startswith("APP-")

    def test_status_is_draft_not_approved(self, client: TestClient):
        """Creating an application must never set status to approved or compliant."""
        resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["status"] not in ("approved", "validation_complete")

    def test_missing_institution_name(self, client: TestClient):
        """Missing required field returns 422."""
        payload = {**VALID_APPLICATION_PAYLOAD}
        del payload["institution_name"]
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_missing_academic_year(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD}
        del payload["academic_year"]
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_invalid_academic_year_format(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD, "academic_year": "2025/26"}
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_invalid_category(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD, "application_category": "not_a_category"}
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_invalid_programme_type(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD, "programme_type": "XYZ"}
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_invalid_email(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD, "applicant_email": "not-an-email"}
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422

    def test_missing_applicant_name(self, client: TestClient):
        payload = {**VALID_APPLICATION_PAYLOAD}
        del payload["applicant_name"]
        resp = client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 422


# ── Application listing ───────────────────────────────────────────────────────

class TestListApplications:
    def test_empty_list(self, client: TestClient):
        resp = client.get("/api/v1/applications")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_lists_created_application(self, client: TestClient):
        client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        resp = client.get("/api/v1/applications")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["institution_name"] == VALID_APPLICATION_PAYLOAD["institution_name"]
        assert item["status"] == "draft"
        # Storage path must not appear in list
        assert "stored_filename" not in str(item)


# ── Application detail ────────────────────────────────────────────────────────

class TestGetApplication:
    def test_get_by_id(self, client: TestClient):
        create_resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        app_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == app_id

    def test_not_found(self, client: TestClient):
        resp = client.get("/api/v1/applications/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_persistence_after_create(self, client: TestClient):
        """Application ID from creation can be retrieved immediately."""
        create_resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        app_id = create_resp.json()["id"]
        get_resp = client.get(f"/api/v1/applications/{app_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["reference_number"] == create_resp.json()["reference_number"]


# ── Application audit trail ───────────────────────────────────────────────────

class TestGetApplicationAuditTrail:
    def test_audit_trail_recorded_on_create(self, client: TestClient):
        """Creating an application automatically generates an audit event."""
        create_resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
        app_id = create_resp.json()["id"]
        audit_resp = client.get(f"/api/v1/applications/{app_id}/audit-trail")
        assert audit_resp.status_code == 200
        body = audit_resp.json()
        assert body["application_id"] == app_id
        assert body["total"] >= 1
        actions = [evt["action"] for evt in body["events"]]
        assert "application.created" in actions
        assert body["events"][0]["id"] is not None

    def test_audit_trail_not_found(self, client: TestClient):
        """Non-existent application returns 404."""
        resp = client.get("/api/v1/applications/00000000-0000-0000-0000-000000000000/audit-trail")
        assert resp.status_code == 404
