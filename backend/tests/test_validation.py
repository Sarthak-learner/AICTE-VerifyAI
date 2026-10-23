"""Tests for Prompt 04: Configurable Validation Rules & Cross-Document Consistency Graph.

All test fixtures use synthetic data. No real institutional documents or records.
"""
import io
import json
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from tests.conftest import VALID_APPLICATION_PAYLOAD, make_pdf
from app.services.validation.normalizer import (
    normalize_text,
    normalize_date,
    normalize_land_area,
    normalize_reference_number,
    are_areas_consistent,
    are_institution_names_consistent,
    are_programmes_consistent,
    are_reference_numbers_consistent,
    are_dates_consistent,
    normalize_intake,
)


# ── Test Helpers ─────────────────────────────────────────────────────────────

def _create_app(client: TestClient) -> str:
    resp = client.post("/api/v1/applications", json=VALID_APPLICATION_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload_synthetic_doc(
    client: TestClient,
    app_id: str,
    text: str,
    filename: str = "document.pdf",
    doc_type: str = "application_form",
) -> str:
    """Build a synthetic text PDF, upload it, and trigger processing so extracted_fields are populated."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")}
    form = {"document_type": doc_type}
    upload_resp = client.post(f"/api/v1/applications/{app_id}/documents", files=files, data=form)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # Trigger processing
    proc_resp = client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/process")
    assert proc_resp.status_code == 202
    return doc_id


# ── 1. Unit Tests for Normalizer ──────────────────────────────────────────────

class TestNormalizer:
    def test_normalize_text_expands_abbreviations(self):
        s = "Govt. College of Engg. & Tech."
        norm = normalize_text(s)
        assert "government" in norm
        assert "engineering" in norm
        assert "technology" in norm
        assert "and" in norm

    def test_normalize_dates(self):
        d1 = normalize_date("2026-10-22")
        assert d1 == date(2026, 10, 22)

        d2 = normalize_date("22/10/2026")
        assert d2 == date(2026, 10, 22)

        d3 = normalize_date("22 October 2026")
        assert d3 == date(2026, 10, 22)

        d4 = normalize_date("October 22, 2026")
        assert d4 == date(2026, 10, 22)

    def test_normalize_land_area_units(self):
        # 5 acres in sq metres: 5 * 4046.856 = 20,234.28
        sqm, unit = normalize_land_area("5 acres")
        assert sqm is not None
        assert abs(sqm - 20234.28) < 1.0

        # 1 hectare in sq metres = 10,000
        sqm_ha, _ = normalize_land_area("1 hectare")
        assert sqm_ha == 10000.0

        # 2000 sq m
        sqm_m, _ = normalize_land_area("2000 sq m")
        assert sqm_m == 2000.0

    def test_are_areas_consistent_within_tolerance(self):
        # 5 acres vs 20,200 sq m (difference < 1%)
        match, expl = are_areas_consistent("5 acres", "20200 sq m")
        assert match is True
        assert expl is None

    def test_are_areas_consistent_genuine_discrepancy(self):
        # 5 acres (~20,234 sq m) vs 2 acres (~8,093 sq m)
        match, expl = are_areas_consistent("5 acres", "2 acres")
        assert match is False
        assert "contradicts" in expl

    def test_are_institution_names_consistent_fuzzy(self):
        # Abbreviation differences should match
        n1 = "Alpha College of Engineering and Technology"
        n2 = "Alpha Coll of Engg & Tech"
        match, _ = are_institution_names_consistent(n1, n2)
        assert match is True

    def test_are_institution_names_consistent_genuine_mismatch(self):
        n1 = "Delhi Institute of Science"
        n2 = "Mumbai Polytechnic College"
        match, expl = are_institution_names_consistent(n1, n2)
        assert match is False
        assert "differs significantly" in expl

    def test_normalize_and_compare_reference_numbers(self):
        # Prefixes and separators normalized
        r1 = "F.No. 123/AICTE-2026"
        r2 = "Ref: 123-aicte-2026"
        match, expl = are_reference_numbers_consistent(r1, r2)
        assert match is True
        assert expl is None

        # Different reference numbers
        r3 = "Order No. 999/2026"
        mismatch, expl2 = are_reference_numbers_consistent(r1, r3)
        assert mismatch is False
        assert "differs from" in expl2

    def test_normalize_and_compare_dates(self):
        # Equivalent date formats match
        d1 = "22/10/2026"
        d2 = "2026-10-22"
        match, expl = are_dates_consistent(d1, d2)
        assert match is True
        assert expl is None

        # Conflicting dates flagged
        d3 = "25/12/2026"
        mismatch, expl2 = are_dates_consistent(d1, d3)
        assert mismatch is False
        assert "contradicts" in expl2



# ── 2. Validation Engine Integration Tests ────────────────────────────────────

class TestValidationEngine:
    def test_validate_empty_application_succeeds(self, client: TestClient):
        """Validating an application with no documents runs cleanly."""
        app_id = _create_app(client)
        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["application_id"] == app_id
        assert data["total_findings"] == 0
        assert data["consistency_graph"]["total_discrepancies"] == 0

    def test_missing_institution_name_triggers_warning(self, client: TestClient):
        """Document with no detectable institution name yields a finding."""
        app_id = _create_app(client)
        # Text with no institution name
        text = "Ref.No.: F.No. 2025/123\nSome general statement with no title header."
        _upload_synthetic_doc(client, app_id, text, "doc_no_name.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        data = resp.json()

        findings = data["findings"]
        rule_codes = [f["rule_code"] for f in findings]
        assert "REQ_INSTITUTION_NAME" in rule_codes
        req_f = next(f for f in findings if f["rule_code"] == "REQ_INSTITUTION_NAME")
        assert req_f["severity"] == "warning"

    def test_expired_document_triggers_finding(self, client: TestClient):
        """Document with an expiry date in the past triggers DOC_EXPIRY_CHECK."""
        app_id = _create_app(client)
        past_date = (date.today() - timedelta(days=60)).strftime("%d/%m/%Y")
        text = f"Institution: Oxford Tech\nRef.No.: APP-2025-01\nValid until: {past_date}"
        _upload_synthetic_doc(client, app_id, text, "expired_doc.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        expiry_f = next((f for f in findings if f["rule_code"] == "DOC_EXPIRY_CHECK"), None)
        assert expiry_f is not None
        assert expiry_f["severity"] == "warning"
        assert past_date in expiry_f["extracted_value"]

    def test_matching_documents_yield_no_discrepancy(self, client: TestClient):
        """Two documents with consistent institution and land area yield 0 discrepancies."""
        app_id = _create_app(client)
        text_a = "Institution Name: Apex Institute of Technology\nLand Area: 5 acres\nRef.No.: F.No. 100/2025"
        text_b = "Institution: Apex Institute of Technology\nTotal Area: 20234 sq m\nCourse: Computer Science"

        _upload_synthetic_doc(client, app_id, text_a, "doc_a.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "doc_b.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        graph = resp.json()["consistency_graph"]
        assert graph["total_discrepancies"] == 0
        assert graph["total_matches"] >= 1

    def test_cross_document_institution_name_mismatch(self, client: TestClient):
        """Two documents with conflicting institution names trigger cross-document discrepancy."""
        app_id = _create_app(client)
        text_a = "Institution Name: Alpha Engineering College\nRef.No.: F.No. 100/2025"
        text_b = "Institution Name: Zenith Business School\nRef.No.: F.No. 200/2025"

        _upload_synthetic_doc(client, app_id, text_a, "deed.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "noc.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["consistency_graph"]["total_discrepancies"] >= 1

        cross_findings = [f for f in data["findings"] if f["rule_code"] == "CROSS_INSTITUTION_NAME_CHECK"]
        assert len(cross_findings) == 1
        finding = cross_findings[0]
        assert finding["document_id"] is None  # Cross-document
        assert "Alpha Engineering College" in finding["extracted_value"]
        assert "Zenith Business School" in finding["extracted_value"]

    def test_cross_document_land_area_discrepancy(self, client: TestClient):
        """Conflicting land area figures across documents generate a finding."""
        app_id = _create_app(client)
        text_a = "Institution Name: City Tech\nLand Area: 10 acres\nRef.No.: F.No. 101/2025"
        text_b = "Institution Name: City Tech\nLand Area: 2.5 acres\nRef.No.: F.No. 101/2025"

        _upload_synthetic_doc(client, app_id, text_a, "land_deed.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "building_statement.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        cross_findings = [f for f in resp.json()["findings"] if f["rule_code"] == "CROSS_LAND_AREA_CHECK"]
        assert len(cross_findings) == 1
        assert "10 acres" in cross_findings[0]["extracted_value"]
        assert "2.5 acres" in cross_findings[0]["extracted_value"]

    def test_validation_is_idempotent(self, client: TestClient):
        """Re-running validation does not create duplicate findings."""
        app_id = _create_app(client)
        text_a = "Institution Name: Alpha Tech\nLand Area: 10 acres\nRef.No.: F.No. 101/2025"
        text_b = "Institution Name: Beta Tech\nLand Area: 2 acres\nRef.No.: F.No. 102/2025"

        _upload_synthetic_doc(client, app_id, text_a, "doc1.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "doc2.pdf")

        # Run 1
        resp1 = client.post(f"/api/v1/applications/{app_id}/validate")
        count1 = resp1.json()["total_findings"]

        # Run 2
        resp2 = client.post(f"/api/v1/applications/{app_id}/validate")
        count2 = resp2.json()["total_findings"]

        assert count1 == count2

    def test_documents_with_no_extracted_fields_shows_clear_explanation(self, client: TestClient):
        """Documents with no extracted comparable fields return explanation, not false proof of consistency."""
        app_id = _create_app(client)
        # Empty / non-matching texts without institutional keywords
        text_a = "Page 1 - General terms and conditions without metadata headers."
        text_b = "Page 2 - Random appendix without numbers or institutional title."

        _upload_synthetic_doc(client, app_id, text_a, "raw1.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "raw2.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        graph = resp.json()["consistency_graph"]

        assert graph["has_comparable_fields"] is False
        assert graph["total_matches"] == 0
        assert graph["total_discrepancies"] == 0
        assert graph["evaluated_pairs"] == 0
        assert "No comparable extracted fields available" in graph["explanation"]

    def test_missing_source_evidence_omits_unsupported_field_comparison(self, client: TestClient):
        """Comparable fields are evaluated only when both documents have actual evidence."""
        app_id = _create_app(client)
        # Doc A has land area + institution; Doc B has institution only
        text_a = "Institution Name: Apex Engineering College\nLand Area: 5 acres"
        text_b = "Institution Name: Apex Engineering College\nCourse: Computer Science"

        _upload_synthetic_doc(client, app_id, text_a, "doc_with_area.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "doc_no_area.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        graph = resp.json()["consistency_graph"]

        # Institution name should match
        inst_comp = next((c for c in graph["comparisons"] if c["field"] == "institution_name"), None)
        assert inst_comp is not None
        assert inst_comp["status"] == "match"

        # Land area should NOT have a comparison entry (missing evidence from Doc B)
        area_comp = next((c for c in graph["comparisons"] if c["field"] == "land_area"), None)
        assert area_comp is None

    def test_cross_document_reference_number_and_dates_mismatch(self, client: TestClient):
        """Conflicting reference numbers and expiry dates produce cross-document discrepancies."""
        app_id = _create_app(client)
        text_a = "Institution Name: Apex Tech\nRef.No.: APP-2026-001\nValid until: 22/10/2026"
        text_b = "Institution Name: Apex Tech\nRef.No.: APP-2026-999\nValid until: 30/12/2028"

        _upload_synthetic_doc(client, app_id, text_a, "cert_a.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "cert_b.pdf")

        resp = client.post(f"/api/v1/applications/{app_id}/validate")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        rule_codes = [f["rule_code"] for f in findings]

        assert "CROSS_REFERENCE_NO_CHECK" in rule_codes
        assert "CROSS_EXPIRY_DATE_CHECK" in rule_codes

        graph = resp.json()["consistency_graph"]
        assert graph["total_discrepancies"] >= 2
        ref_comp = next(c for c in graph["comparisons"] if c["field"] == "reference_number")
        assert ref_comp["status"] == "discrepancy"
        date_comp = next(c for c in graph["comparisons"] if c["field"] == "expiry_date")
        assert date_comp["status"] == "discrepancy"


# ── 3. Reviewer Actions & Status Updates Tests ───────────────────────────────

class TestReviewerActions:
    def test_update_finding_status_and_notes(self, client: TestClient):
        """Reviewer can mark finding as under_review, resolved, or requires_clarification with notes."""
        app_id = _create_app(client)
        text = "Ref.No.: F.No. 123/2025\nGeneral text without institution header."
        _upload_synthetic_doc(client, app_id, text, "doc.pdf")

        client.post(f"/api/v1/applications/{app_id}/validate")
        findings_resp = client.get(f"/api/v1/applications/{app_id}/findings")
        finding_id = findings_resp.json()["items"][0]["id"]

        # Review finding: change to requires_clarification
        patch_resp = client.patch(
            f"/api/v1/applications/{app_id}/findings/{finding_id}",
            json={
                "status": "requires_clarification",
                "resolution_note": "Requesting affidavit page 1 rescan from institution.",
                "reviewer_label": "Senior AICTE Officer",
            },
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["status"] == "requires_clarification"
        assert body["resolution_note"] == "Requesting affidavit page 1 rescan from institution."

        # Verify resolution is preserved when re-running validation
        client.post(f"/api/v1/applications/{app_id}/validate")
        get_resp = client.get(f"/api/v1/applications/{app_id}/findings")
        updated = next(f for f in get_resp.json()["items"] if f["id"] == finding_id)
        assert updated["status"] == "requires_clarification"
        assert updated["resolution_note"] == "Requesting affidavit page 1 rescan from institution."

    def test_get_consistency_graph_endpoint(self, client: TestClient):
        """GET /consistency-graph returns valid graph nodes, edges, and side-by-side comparisons."""
        app_id = _create_app(client)
        text_a = "Institution Name: Model College\nLand Area: 5 acres"
        text_b = "Institution Name: Model College\nLand Area: 5 acres"
        _upload_synthetic_doc(client, app_id, text_a, "doc_1.pdf")
        _upload_synthetic_doc(client, app_id, text_b, "doc_2.pdf")

        resp = client.get(f"/api/v1/applications/{app_id}/consistency-graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert "nodes" in graph
        assert "edges" in graph
        assert "comparisons" in graph
        assert len(graph["nodes"]) >= 2
        assert graph["total_matches"] >= 1

    def test_rules_listing_endpoint(self, client: TestClient):
        """GET /rules lists configured validation rules with is_demo flag."""
        resp = client.get("/api/v1/rules")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 5
        assert any(r["code"] == "REQ_INSTITUTION_NAME" for r in body["items"])
        assert all(r["is_demo"] is True for r in body["items"])
