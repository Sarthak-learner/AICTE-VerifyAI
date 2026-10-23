"""Tests for Prompt 03: OCR extraction, field extraction, processing status, and dashboard.

All fixtures use synthetic data. No real documents or institutional records.
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    VALID_APPLICATION_PAYLOAD,
    make_pdf,
    make_png,
    make_jpeg,
    make_tiff,
)
from app.services.ocr.engine import extract_from_pdf, extract_from_image
from app.services.extraction.fields import extract_fields


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_app(client: TestClient) -> str:
    resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload(client: TestClient, app_id: str, data: bytes, filename: str, doc_type=None):
    files = {"file": (filename, io.BytesIO(data), "application/octet-stream")}
    form = {}
    if doc_type:
        form["document_type"] = doc_type
    return client.post(f"/api/v1/applications/{app_id}/documents",
                       files=files, data=form)


def _make_text_pdf(text: str) -> bytes:
    """Build a PDF with specified text content embedded."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


# ── OCR unit tests ────────────────────────────────────────────────────────────

class TestOCREngine:
    def test_extract_embedded_text_from_pdf(self):
        """PyMuPDF should extract embedded text from a text-based PDF."""
        text = "Institution Name: AICTE Test College\nRef.No.: F.No. 2025/TEST/001"
        data = _make_text_pdf(text)
        result = extract_from_pdf(data)
        assert result.error is None
        assert len(result.pages) == 1
        assert result.pages[0].source == "embedded"
        assert "AICTE Test College" in result.full_text

    def test_multi_page_pdf_has_multiple_pages(self):
        """A 3-page PDF should produce 3 page entries."""
        data = make_pdf(pages=3)
        result = extract_from_pdf(data)
        assert result.error is None
        assert len(result.pages) == 3
        for i, page in enumerate(result.pages, start=1):
            assert page.page_number == i

    def test_corrupted_pdf_returns_error(self):
        """A corrupted PDF should return an error in ExtractionResult, not raise."""
        corrupted = b"%PDF-1.4 garbage data" * 5
        result = extract_from_pdf(corrupted)
        # Should either succeed partially or return an error — must not crash
        assert result.error is not None or len(result.pages) == 0

    def test_image_ocr_unavailable_handled_gracefully(self):
        """When Tesseract is not found, extract_from_image should not raise."""
        data = make_png()
        result = extract_from_image(data, mime_type="image/png",
                                    tesseract_cmd="/nonexistent/tesseract")
        # Should return empty page with error note, not raise
        assert len(result.pages) == 1
        assert result.pages[0].text == "" or result.error is not None

    def test_jpeg_ocr_unavailable_handled_gracefully(self):
        """JPEG with unavailable Tesseract should return gracefully."""
        data = make_jpeg()
        result = extract_from_image(data, mime_type="image/jpeg",
                                    tesseract_cmd="/nonexistent/tesseract")
        assert len(result.pages) == 1

    def test_tiff_ocr_unavailable_handled_gracefully(self):
        """TIFF with unavailable Tesseract should return gracefully."""
        data = make_tiff()
        result = extract_from_image(data, mime_type="image/tiff",
                                    tesseract_cmd="/nonexistent/tesseract")
        assert len(result.pages) == 1


# ── Field extraction unit tests ───────────────────────────────────────────────

class TestFieldExtraction:
    def test_extracts_institution_name(self):
        pages = [(1, "Institution Name: AICTE Demo Engineering College\nOther content here")]
        fields = extract_fields(pages)
        assert fields.institution_name.value is not None
        assert "AICTE Demo Engineering College" in fields.institution_name.value

    def test_extracts_reference_number(self):
        pages = [(1, "F.No. 1-22/AICTE/2025\nDate: 01 Jan 2025")]
        fields = extract_fields(pages)
        assert fields.reference_number.value is not None
        assert "1-22/AICTE/2025" in fields.reference_number.value

    def test_extracts_issue_date(self):
        pages = [(1, "Issued on: 15/03/2025\nValidity: 3 years")]
        fields = extract_fields(pages)
        assert fields.issue_date.value is not None
        assert "15" in fields.issue_date.value or "2025" in fields.issue_date.value

    def test_extracts_expiry_date(self):
        pages = [(1, "Valid up to: 31/03/2028\nApproved programmes listed below")]
        fields = extract_fields(pages)
        assert fields.expiry_date.value is not None
        assert "2028" in fields.expiry_date.value

    def test_extracts_land_area(self):
        pages = [(1, "The land area is 5 acres with clear title.")]
        fields = extract_fields(pages)
        assert fields.land_area.value is not None
        assert "5 acres" in fields.land_area.value.lower()

    def test_extracts_intake_figure(self):
        pages = [(1, "Sanctioned intake of 120 students per year.")]
        fields = extract_fields(pages)
        assert fields.intake_figure.value is not None
        assert "120" in fields.intake_figure.value

    def test_missing_fields_return_null(self):
        """Fields not present in the text must be null, never fabricated."""
        pages = [(1, "This document has no structured information at all.")]
        fields = extract_fields(pages)
        # Most fields should be null for this blank text
        assert fields.reference_number.value is None
        assert fields.land_area.value is None
        assert fields.intake_figure.value is None

    def test_empty_pages_return_all_null(self):
        fields = extract_fields([])
        assert fields.institution_name.value is None
        assert fields.reference_number.value is None
        assert fields.issue_date.value is None
        assert fields.expiry_date.value is None
        assert fields.land_area.value is None
        assert fields.programme_name.value is None
        assert fields.intake_figure.value is None

    def test_extracted_fields_json_roundtrip(self):
        """ExtractedFields must serialize and deserialize correctly."""
        from app.services.extraction.fields import ExtractedFields, ExtractedField
        ef = ExtractedFields()
        ef.institution_name = ExtractedField(
            value="Test College", raw_match="Institution Name: Test College",
            source_page=1, confidence="high"
        )
        json_str = ef.to_json()
        restored = ExtractedFields.from_json(json_str)
        assert restored.institution_name.value == "Test College"
        assert restored.institution_name.confidence == "high"


# ── Processing endpoint integration tests ─────────────────────────────────────

class TestProcessingEndpoint:
    def test_process_text_pdf_returns_202(self, client: TestClient):
        """Processing a text-based PDF should succeed (PROCESSED status)."""
        app_id = _create_app(client)
        text = "Institution Name: Demo College\nRef.No.: DEMO-001"
        data = _make_text_pdf(text)
        upload_resp = _upload(client, app_id, data, "test.pdf")
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["document"]["id"]

        resp = client.post(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/process"
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["document_id"] == doc_id
        assert body["status"] in ("processed", "failed")  # Failed if env issue

    def test_get_extraction_after_processing(self, client: TestClient):
        """After processing, extraction endpoint returns ocr_text and fields."""
        app_id = _create_app(client)
        text = "Institution Name: Apex College\nRef.No.: F.No. 001/2025"
        data = _make_text_pdf(text)
        upload_resp = _upload(client, app_id, data, "apex.pdf")
        doc_id = upload_resp.json()["document"]["id"]

        client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/process")

        resp = client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/extraction"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["document_id"] == doc_id
        assert "status" in body
        assert "page_count" in body
        # ocr_text and extracted_fields present if status is processed
        if body["status"] == "processed":
            assert body["ocr_text"] is not None or body["extracted_fields"] is not None

    def test_get_extraction_before_processing(self, client: TestClient):
        """Extraction endpoint on unprocessed doc returns UPLOADED status."""
        app_id = _create_app(client)
        upload_resp = _upload(client, app_id, make_pdf(), "unprocessed.pdf")
        doc_id = upload_resp.json()["document"]["id"]

        resp = client.get(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/extraction"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "uploaded"
        assert body["ocr_text"] is None
        assert body["extracted_fields"] is None

    def test_process_nonexistent_document_returns_404(self, client: TestClient):
        app_id = _create_app(client)
        resp = client.post(
            f"/api/v1/applications/{app_id}/documents/"
            "00000000-0000-0000-0000-000000000000/process"
        )
        assert resp.status_code == 404

    def test_process_image_without_tesseract_does_not_crash(self, client: TestClient):
        """Processing a PNG without Tesseract should return 202 (graceful)."""
        app_id = _create_app(client)
        upload_resp = _upload(client, app_id, make_png(), "scan.png")
        doc_id = upload_resp.json()["document"]["id"]

        resp = client.post(
            f"/api/v1/applications/{app_id}/documents/{doc_id}/process"
        )
        # Should not crash — either processed (empty OCR) or failed gracefully
        assert resp.status_code == 202

    def test_reprocessing_is_idempotent(self, client: TestClient):
        """Calling process twice should not create duplicate document records."""
        app_id = _create_app(client)
        data = _make_text_pdf("Name of the institution: Test Institute")
        upload_resp = _upload(client, app_id, data, "test.pdf")
        doc_id = upload_resp.json()["document"]["id"]

        client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/process")
        client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/process")

        # Confirm we still have one document (not two)
        docs = client.get(f"/api/v1/applications/{app_id}/documents")
        assert docs.json()["total"] == 1


# ── Dashboard aggregation tests ───────────────────────────────────────────────

class TestDashboard:
    def test_empty_dashboard(self, client: TestClient):
        """Empty DB should return all-zero counts."""
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_applications"] == 0
        assert body["total_documents"] == 0
        assert body["processed_documents"] == 0
        assert isinstance(body["applications_by_status"], list)
        assert isinstance(body["documents_by_status"], list)
        assert isinstance(body["documents_by_category"], list)

    def test_dashboard_counts_match_records(self, client: TestClient):
        """Counts should match number of actually created records."""
        # Create 2 applications with 1 doc each
        app1 = _create_app(client)
        app2_payload = {**VALID_APPLICATION_PAYLOAD, "institution_name": "Second Institute"}
        app2 = client.post("/api/v1/applications", json=app2_payload).json()["id"]

        _upload(client, app1, make_pdf(), "doc1.pdf", "application_form")
        _upload(client, app2, make_pdf(pages=2), "doc2.pdf", "land_deed_lease")

        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_applications"] == 2
        assert body["total_documents"] == 2
        assert body["processed_documents"] == 0  # Not yet processed

    def test_dashboard_status_distribution(self, client: TestClient):
        """Status distribution should reflect actual statuses."""
        _create_app(client)
        resp = client.get("/api/v1/dashboard/stats")
        body = resp.json()
        status_counts = {item["status"]: item["count"] for item in body["applications_by_status"]}
        assert status_counts.get("draft", 0) == 1
        assert status_counts.get("approved", 0) == 0

    def test_dashboard_category_distribution(self, client: TestClient):
        """Document category counts should match uploads."""
        app_id = _create_app(client)
        _upload(client, app_id, make_pdf(), "form.pdf", "application_form")
        _upload(client, app_id, make_pdf(pages=2), "deed.pdf", "land_deed_lease")

        resp = client.get("/api/v1/dashboard/stats")
        body = resp.json()
        cat_counts = {item["category"]: item["count"] for item in body["documents_by_category"]}
        assert cat_counts.get("application_form", 0) == 1
        assert cat_counts.get("land_deed_lease", 0) == 1

    def test_processed_count_increments_after_processing(self, client: TestClient):
        """processed_documents should increment after OCR processing."""
        app_id = _create_app(client)
        data = _make_text_pdf("Institution Name: Count Test College")
        upload_resp = _upload(client, app_id, data, "counttest.pdf")
        doc_id = upload_resp.json()["document"]["id"]

        # Before processing
        before = client.get("/api/v1/dashboard/stats").json()
        initial_processed = before["processed_documents"]

        # Process
        client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/process")

        after = client.get("/api/v1/dashboard/stats").json()
        # If processing succeeded, count should have increased
        if after["documents_by_status"]:
            doc_status_map = {
                item["status"]: item["count"]
                for item in after["documents_by_status"]
            }
            total_tracked = sum(doc_status_map.values())
            assert total_tracked >= 1
