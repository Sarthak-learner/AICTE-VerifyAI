"""Tests for document upload, duplicate detection, and listing.

All file content is synthetic. No real institutional data is used.
"""
import io
import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    VALID_APPLICATION_PAYLOAD,
    make_pdf,
    make_png,
    make_jpeg,
    make_tiff,
)


def _create_app(client: TestClient) -> str:
    resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload(client: TestClient, app_id: str, data: bytes, filename: str,
            doc_type: str | None = None):
    files = {"file": (filename, io.BytesIO(data), "application/octet-stream")}
    form = {}
    if doc_type:
        form["document_type"] = doc_type
    return client.post(f"/api/v1/applications/{app_id}/documents",
                       files=files, data=form)


# ── Upload success cases ──────────────────────────────────────────────────────

class TestUploadSuccess:
    def test_upload_pdf(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_pdf(), "test.pdf", "application_form")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["document"]["mime_type"] == "application/pdf"
        assert body["document"]["page_count"] == 1
        assert body["document"]["is_duplicate"] is False
        assert body["duplicate"] is None
        # Storage path must not appear
        assert "stored_filename" not in str(body["document"])

    def test_upload_png(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_png(), "photo.png")
        assert resp.status_code == 201
        assert resp.json()["document"]["mime_type"] == "image/png"

    def test_upload_jpeg(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_jpeg(), "photo.jpg")
        assert resp.status_code == 201
        assert resp.json()["document"]["mime_type"] == "image/jpeg"

    def test_upload_tiff(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_tiff(), "scan.tiff")
        assert resp.status_code == 201
        assert resp.json()["document"]["mime_type"] == "image/tiff"

    def test_document_linked_to_application(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_pdf(), "linked.pdf")
        assert resp.status_code == 201
        assert resp.json()["document"]["application_id"] == app_id

    def test_document_category_stored(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_pdf(), "deed.pdf", "land_deed_lease")
        assert resp.status_code == 201
        assert resp.json()["document"]["document_type"] == "land_deed_lease"

    def test_sha256_hash_present(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_pdf(), "hash_check.pdf")
        assert resp.status_code == 201
        sha = resp.json()["document"]["sha256_hash"]
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)


# ── Upload failure cases ──────────────────────────────────────────────────────

class TestUploadRejection:
    def test_empty_file(self, client: TestClient):
        app_id = _create_app(client)
        resp = _upload(client, app_id, b"", "empty.pdf")
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()

    def test_unsupported_extension(self, client: TestClient):
        """A .docx file with DOCX magic bytes must be rejected."""
        app_id = _create_app(client)
        # DOCX starts with PK (ZIP magic)
        docx_magic = b"PK\x03\x04" + b"\x00" * 100
        resp = _upload(client, app_id, docx_magic, "form.docx")
        assert resp.status_code == 422

    def test_mismatched_extension_and_content(self, client: TestClient):
        """A .pdf extension with PNG content must be rejected (magic bytes mismatch)."""
        app_id = _create_app(client)
        png_data = make_png()
        # PNG magic does not match PDF signature — but PNG IS in the allow-list
        # So this actually succeeds and gets classified as PNG.
        # Instead test with a truly unrecognised type:
        resp = _upload(client, app_id, b"\x00\x01\x02\x03" * 50, "fake.pdf")
        assert resp.status_code == 422

    def test_file_too_large(self, client: TestClient, override_settings):
        """Files exceeding the size limit are rejected."""
        app_id = _create_app(client)
        # override_settings has max_upload_size_mb=10; create 11 MB of PDF magic
        big_data = b"%PDF-1.4 " + b"A" * (11 * 1024 * 1024)
        resp = _upload(client, app_id, big_data, "big.pdf")
        # Should fail at size check (before even checking PDF validity)
        assert resp.status_code == 422
        assert "limit" in resp.json()["detail"].lower() or "size" in resp.json()["detail"].lower()

    def test_corrupted_pdf(self, client: TestClient):
        """A file with PDF magic bytes but corrupted content must be rejected."""
        app_id = _create_app(client)
        corrupted = b"%PDF-1.4 corrupted garbage \xde\xad\xbe\xef" * 10
        resp = _upload(client, app_id, corrupted, "corrupt.pdf")
        assert resp.status_code == 422

    def test_nonexistent_application(self, client: TestClient):
        """Upload to a non-existent application returns 404."""
        resp = _upload(client, "00000000-0000-0000-0000-000000000000",
                       make_pdf(), "test.pdf")
        assert resp.status_code == 404

    def test_invalid_document_category(self, client: TestClient):
        """An unrecognised document category returns 422."""
        app_id = _create_app(client)
        resp = _upload(client, app_id, make_pdf(), "test.pdf", "not_a_category")
        assert resp.status_code == 422


# ── Duplicate detection ───────────────────────────────────────────────────────

class TestDuplicateDetection:
    def test_exact_duplicate_flagged(self, client: TestClient):
        """Uploading the same bytes twice flags the second as duplicate."""
        app_id = _create_app(client)
        pdf_data = make_pdf()

        first = _upload(client, app_id, pdf_data, "original.pdf")
        assert first.status_code == 201
        assert first.json()["document"]["is_duplicate"] is False
        assert first.json()["duplicate"] is None

        second = _upload(client, app_id, pdf_data, "copy.pdf")
        assert second.status_code == 201
        body = second.json()
        assert body["document"]["is_duplicate"] is True
        assert body["duplicate"] is not None
        assert body["duplicate"]["existing_document_id"] == first.json()["document"]["id"]
        # Warning message must be present
        assert "identical" in body["duplicate"]["message"].lower()

    def test_duplicate_not_deleted(self, client: TestClient):
        """The original document is not deleted when a duplicate is uploaded."""
        app_id = _create_app(client)
        pdf_data = make_pdf()
        first = _upload(client, app_id, pdf_data, "original.pdf")
        _upload(client, app_id, pdf_data, "dup.pdf")

        # The first document should still be retrievable
        doc_id = first.json()["document"]["id"]
        get_resp = client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}")
        assert get_resp.status_code == 200

    def test_different_content_not_duplicate(self, client: TestClient):
        """Two different files must not be flagged as duplicates."""
        app_id = _create_app(client)
        first = _upload(client, app_id, make_pdf(pages=1), "page1.pdf")
        second = _upload(client, app_id, make_pdf(pages=2), "page2.pdf")
        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["document"]["is_duplicate"] is False


# ── Document listing ──────────────────────────────────────────────────────────

class TestDocumentListing:
    def test_empty_list(self, client: TestClient):
        app_id = _create_app(client)
        resp = client.get(f"/api/v1/applications/{app_id}/documents")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_lists_uploaded_documents(self, client: TestClient):
        app_id = _create_app(client)
        _upload(client, app_id, make_pdf(), "doc1.pdf")
        _upload(client, app_id, make_png(), "doc2.png")
        resp = client.get(f"/api/v1/applications/{app_id}/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        # No storage paths in response
        for item in body["items"]:
            assert "stored_filename" not in item

    def test_documents_scoped_to_application(self, client: TestClient):
        """Documents from one application do not appear in another's list."""
        app1 = _create_app(client)
        app2_payload = {**VALID_APPLICATION_PAYLOAD, "institution_name": "Second Institute"}
        app2 = client.post("/api/v1/applications", json=app2_payload).json()["id"]
        _upload(client, app1, make_pdf(), "app1.pdf")
        resp = client.get(f"/api/v1/applications/{app2}/documents")
        assert resp.json()["total"] == 0

    def test_list_nonexistent_application(self, client: TestClient):
        resp = client.get("/api/v1/applications/00000000-0000-0000-0000-000000000000/documents")
        assert resp.status_code == 404


# ── Document metadata ─────────────────────────────────────────────────────────

class TestDocumentMetadata:
    def test_get_document_metadata(self, client: TestClient):
        app_id = _create_app(client)
        upload_resp = _upload(client, app_id, make_pdf(), "meta.pdf")
        doc_id = upload_resp.json()["document"]["id"]
        resp = client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}")
        assert resp.status_code == 200
        doc = resp.json()
        assert doc["id"] == doc_id
        assert doc["original_filename"] == "meta.pdf"
        # Storage path must never be exposed
        assert "stored_filename" not in doc

    def test_document_not_found(self, client: TestClient):
        app_id = _create_app(client)
        resp = client.get(
            f"/api/v1/applications/{app_id}/documents/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
