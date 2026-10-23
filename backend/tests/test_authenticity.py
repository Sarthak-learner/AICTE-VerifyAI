"""Tests for Document Authenticity Screening (Prompt 05).

Verifies:
- Matching and mismatching SHA-256 hashes.
- Valid, malformed, and encrypted PDFs.
- Missing and future-dated metadata.
- PDFs with and without digital signature fields.
- Image resolution and aspect ratio indicators.
- Textual header consistency cross-referencing.
- Unavailable checks on non-PDF formats.
- Idempotent reruns preserving reviewer status and notes.
- Reviewer status updates and audit events.
- Error handling on non-existent applications.
"""
import io
import json
import hashlib
from datetime import datetime, timezone, timedelta
import pytest
import fitz
from PIL import Image

from app.models.application import Application, ApplicationStatus
from app.models.document import Document, DocumentStatus
from app.models.authenticity import AuthenticityCheck, AuthenticityResult
from app.models.finding import FindingStatus
from app.models.audit import AuditEvent
from app.services.authenticity.screening import (
    check_file_integrity,
    check_pdf_metadata,
    check_pdf_structure,
    check_image_indicators,
    check_text_indicators,
    check_signature_presence,
    run_document_screening,
    run_application_screening,
)
from tests.conftest import VALID_APPLICATION_PAYLOAD, make_pdf, make_png, make_jpeg


def _make_signed_pdf() -> bytes:
    """Create a minimal PDF with a digital signature container."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Signed Document Test")
    data = doc.tobytes()
    doc.close()
    # Digital signature dictionary markers (Adobe PKCS#7 format)
    return data + b"\n% /ByteRange [ 0 1000 2000 1000 ] /SubFilter /adbe.pkcs7.detached /Type /Sig\n"


def _make_encrypted_pdf() -> bytes:
    """Create an encrypted/password-protected PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential Document")
    buf = io.BytesIO()
    doc.save(
        buf,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="adminpass",
        user_pw="userpass",
    )
    doc.close()
    return buf.getvalue()


def _make_future_metadata_pdf() -> bytes:
    """Create a PDF with metadata creation date in year 2099."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Future Dated Doc")
    doc.set_metadata({
        "title": "Future Certificate",
        "creator": "TimeMachine",
        "producer": "FuturisticPDF",
        "creationDate": "D:20990101120000+00'00'",
        "modDate": "D:20990101120000+00'00'",
    })
    data = doc.tobytes()
    doc.close()
    return data


def _make_inverted_metadata_pdf() -> bytes:
    """Create a PDF where modification date precedes creation date."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Inverted Metadata Doc")
    doc.set_metadata({
        "title": "Anomaly Certificate",
        "creator": "TestScanner",
        "producer": "LibTest",
        "creationDate": "D:20240601120000+00'00'",
        "modDate": "D:20200101120000+00'00'",
    })
    data = doc.tobytes()
    doc.close()
    return data


# ── Unit tests for individual deterministic checks ───────────────────────────

def test_file_integrity_check_matching():
    pdf_bytes = make_pdf(1)
    correct_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc = Document(id="d1", mime_type="application/pdf", sha256_hash=correct_hash)

    result = check_file_integrity(doc, pdf_bytes)
    assert result["result"] == AuthenticityResult.PASS
    assert "No indicator detected" in result["explanation"]
    assert result["evidence"]["matched"] is True


def test_file_integrity_check_mismatch():
    pdf_bytes = make_pdf(1)
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    doc = Document(id="d1", mime_type="application/pdf", sha256_hash=wrong_hash)

    result = check_file_integrity(doc, pdf_bytes)
    assert result["result"] == AuthenticityResult.REVIEW
    assert "does not match" in result["explanation"]
    assert result["evidence"]["matched"] is False


def test_file_integrity_check_missing_file():
    doc = Document(id="d1", mime_type="application/pdf", sha256_hash="abc")
    result = check_file_integrity(doc, None)
    assert result["result"] == AuthenticityResult.REVIEW
    assert "unavailable" in result["explanation"]


def test_pdf_metadata_future_date_anomaly():
    data = _make_future_metadata_pdf()
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_pdf_metadata(doc, data)
    assert res["result"] == AuthenticityResult.REVIEW
    assert "future" in res["explanation"].lower()


def test_pdf_metadata_inverted_date_anomaly():
    data = _make_inverted_metadata_pdf()
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_pdf_metadata(doc, data)
    assert res["result"] == AuthenticityResult.REVIEW
    assert "precedes" in res["explanation"].lower()


def test_pdf_metadata_unavailable_for_image():
    png_bytes = make_png()
    doc = Document(id="d1", mime_type="image/png")
    res = check_pdf_metadata(doc, png_bytes)
    assert res["result"] == AuthenticityResult.UNAVAILABLE


def test_pdf_structure_valid():
    pdf_bytes = make_pdf(2)
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_pdf_structure(doc, pdf_bytes)
    assert res["result"] == AuthenticityResult.PASS
    assert res["evidence"]["page_count"] == 2


def test_pdf_structure_encrypted():
    enc_bytes = _make_encrypted_pdf()
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_pdf_structure(doc, enc_bytes)
    assert res["result"] == AuthenticityResult.REVIEW
    assert "encrypted" in res["explanation"].lower()


def test_pdf_structure_malformed():
    corrupt_bytes = b"%PDF-1.4\ncorrupted random bytes that do not form a valid pdf"
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_pdf_structure(doc, corrupt_bytes)
    assert res["result"] == AuthenticityResult.REVIEW
    assert "parsing" in res["explanation"].lower() or "malformed" in res["explanation"].lower()


def test_signature_presence_detected():
    signed_bytes = _make_signed_pdf()
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_signature_presence(doc, signed_bytes)
    assert res["result"] == AuthenticityResult.PASS
    assert res["evidence"]["signature_field_detected"] is True
    assert "Digital signature field detected" in res["explanation"]


def test_signature_presence_unsigned():
    plain_bytes = make_pdf(1)
    doc = Document(id="d1", mime_type="application/pdf")
    res = check_signature_presence(doc, plain_bytes)
    assert res["result"] == AuthenticityResult.PASS
    assert res["evidence"]["signature_field_detected"] is False
    assert "No digital signature field present" in res["explanation"]


def test_image_indicators_tiny_resolution():
    buf = io.BytesIO()
    img = Image.new("RGB", (30, 30), color="blue")
    img.save(buf, format="PNG")
    doc = Document(id="d1", mime_type="image/png")
    res = check_image_indicators(doc, buf.getvalue())
    assert res["result"] == AuthenticityResult.REVIEW
    assert "unusually low" in res["explanation"].lower()


def test_text_indicators_conflict_with_application():
    app = Application(id="app1", institution_name="Indian Institute of Technology Bombay")
    extracted_data = {
        "institution_name": {
            "value": "National Institute of Technology Trichy",
            "source_page": 1,
        }
    }
    doc = Document(id="d1", mime_type="application/pdf", extracted_fields=json.dumps(extracted_data))
    res = check_text_indicators(doc, app)
    assert res["result"] == AuthenticityResult.REVIEW
    assert "conflicts" in res["explanation"].lower()


def test_text_indicators_match_with_application():
    app = Application(id="app1", institution_name="Demo Institute of Technology")
    extracted_data = {
        "institution_name": {
            "value": "Demo Institute of Technology",
            "source_page": 1,
        }
    }
    doc = Document(id="d1", mime_type="application/pdf", extracted_fields=json.dumps(extracted_data))
    res = check_text_indicators(doc, app)
    assert res["result"] == AuthenticityResult.PASS


# ── Integration tests via FastAPI client ─────────────────────────────────────

def test_authenticity_screen_api_end_to_end(client, db, storage):
    # 1. Create Application
    create_resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
    assert create_resp.status_code == 201
    app_id = create_resp.json()["id"]

    # 2. Upload a valid signed PDF
    signed_pdf = _make_signed_pdf()
    up_resp = client.post(
        f"/api/v1/applications/{app_id}/documents",
        files={"file": ("signed_noc.pdf", io.BytesIO(signed_pdf), "application/pdf")},
        data={"document_type": "noc_certificate"},
    )
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["document"]["id"]

    # 3. Upload an image
    buf = io.BytesIO()
    img = Image.new("RGB", (800, 600), color="white")
    img.save(buf, format="JPEG")
    up_img = client.post(
        f"/api/v1/applications/{app_id}/documents",
        files={"file": ("site_photo.jpg", io.BytesIO(buf.getvalue()), "image/jpeg")},
        data={"document_type": "other"},
    )
    assert up_img.status_code == 201

    # 4. Run Authenticity Screening
    screen_resp = client.post(f"/api/v1/applications/{app_id}/authenticity-screen")
    assert screen_resp.status_code == 200
    screen_data = screen_resp.json()

    assert screen_data["application_id"] == app_id
    assert screen_data["total_checks"] == 12  # 6 checks * 2 documents
    assert len(screen_data["documents"]) == 2
    assert screen_data["total_passed"] > 0

    # 5. Retrieve Authenticity Checks via GET
    get_resp = client.get(f"/api/v1/applications/{app_id}/authenticity-checks")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["total_checks"] == 12

    # 6. Check filter by document_id
    doc_filter_resp = client.get(f"/api/v1/applications/{app_id}/authenticity-checks?document_id={doc_id}")
    assert doc_filter_resp.status_code == 200
    doc_checks = [c for c in doc_filter_resp.json()["checks"] if c["document_id"] == doc_id]
    assert len(doc_checks) == 6

    # 7. Update Reviewer Status and Note on a check
    target_check = doc_checks[0]
    patch_resp = client.patch(
        f"/api/v1/applications/{app_id}/authenticity-checks/{target_check['id']}",
        json={
            "reviewer_status": "under_review",
            "reviewer_notes": "Officer verified signature field visually.",
            "reviewer_label": "Senior Inspector",
        },
    )
    assert patch_resp.status_code == 200
    patched_check = patch_resp.json()
    assert patched_check["reviewer_status"] == "under_review"
    assert patched_check["reviewer_notes"] == "Officer verified signature field visually."

    # 8. Check that Audit Log was recorded
    audit_events = db.query(AuditEvent).filter(AuditEvent.application_id == app_id).all()
    actions = [a.action for a in audit_events]
    assert "authenticity.screened" in actions
    assert "authenticity.reviewed" in actions

    # 9. Test Idempotency: Re-running screening must preserve reviewer status and notes!
    rescreen_resp = client.post(f"/api/v1/applications/{app_id}/authenticity-screen")
    assert rescreen_resp.status_code == 200
    after_rescreen_resp = client.get(f"/api/v1/applications/{app_id}/authenticity-checks")
    persisted_target = next(c for c in after_rescreen_resp.json()["checks"] if c["id"] == target_check["id"])
    assert persisted_target["reviewer_status"] == "under_review"
    assert persisted_target["reviewer_notes"] == "Officer verified signature field visually."


def test_authenticity_screen_not_found(client):
    resp = client.post("/api/v1/applications/non-existent-id/authenticity-screen")
    assert resp.status_code == 404
