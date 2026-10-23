"""Validation & Cross-Document Consistency Engine for AICTE VerifyAI.

Evaluates:
  1. Single-document configurable validation rules (presence, date expiry, demo thresholds).
  2. Cross-document consistency graph (pairwise comparison of normalized fields across documents).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.document import Document, DocumentStatus
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.audit import AuditEvent
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

logger = logging.getLogger(__name__)


def _parse_extracted_fields(doc: Document) -> Dict[str, Any]:
    """Safely parse extracted_fields JSON from a Document."""
    if not doc.extracted_fields:
        return {}
    if isinstance(doc.extracted_fields, dict):
        return doc.extracted_fields
    try:
        return json.loads(doc.extracted_fields)
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_field_entry(fields: Dict[str, Any], field_name: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """Return (value, raw_match, page_number) for a given field key."""
    item = fields.get(field_name)
    if not item or not isinstance(item, dict):
        return (None, None, None)
    val = item.get("value")
    raw = item.get("raw_match")
    page = item.get("source_page")
    return (str(val) if val is not None else None, str(raw) if raw is not None else None, page)


def evaluate_document_rules(doc: Document) -> List[Dict[str, Any]]:
    """Evaluate single-document rules against a document's extracted fields."""
    findings_to_create: List[Dict[str, Any]] = []
    fields = _parse_extracted_fields(doc)

    inst_val, inst_raw, inst_page = _get_field_entry(fields, "institution_name")
    ref_val, ref_raw, ref_page = _get_field_entry(fields, "reference_number")
    expiry_val, expiry_raw, expiry_page = _get_field_entry(fields, "expiry_date")
    intake_val, intake_raw, intake_page = _get_field_entry(fields, "intake_figure")
    land_val, land_raw, land_page = _get_field_entry(fields, "land_area")

    # 1. Institution Name Presence
    if not inst_val:
        findings_to_create.append({
            "rule_code": "REQ_INSTITUTION_NAME",
            "rule_name": "Institution Name Presence Check",
            "severity": FindingSeverity.WARNING,
            "title": f"Institution name not detected in '{doc.original_filename}'",
            "detail": (
                f"OCR did not identify a standard institutional header in '{doc.original_filename}'. "
                "This may indicate low scan resolution, non-standard layout, or a missing title block. "
                "Advisory finding — does not confirm non-compliance."
            ),
            "document_id": doc.id,
            "page_number": None,
            "extracted_value": None,
            "expected_value": "Institution name in document header",
            "evidence": {
                "field": "institution_name",
                "document_filename": doc.original_filename,
                "advisory": True,
            },
        })

    # 2. Reference Number Presence
    if not ref_val:
        findings_to_create.append({
            "rule_code": "REQ_REFERENCE_NO",
            "rule_name": "Reference Number Presence Check",
            "severity": FindingSeverity.INFO,
            "title": f"Document reference number not detected in '{doc.original_filename}'",
            "detail": (
                f"No reference number or order ID was extracted from '{doc.original_filename}'. "
                "Reviewer should verify if this document requires an official order or dispatch number."
            ),
            "document_id": doc.id,
            "page_number": None,
            "extracted_value": None,
            "expected_value": "Order / Letter / Ref No.",
            "evidence": {
                "field": "reference_number",
                "document_filename": doc.original_filename,
            },
        })

    # 3. Document Expiry Date Check
    if expiry_val:
        parsed_expiry = normalize_date(expiry_val)
        today = datetime.now(timezone.utc).date()
        if parsed_expiry and parsed_expiry < today:
            findings_to_create.append({
                "rule_code": "DOC_EXPIRY_CHECK",
                "rule_name": "Document Validity & Expiry Check",
                "severity": FindingSeverity.WARNING,
                "title": f"Document validity expired: '{doc.original_filename}'",
                "detail": (
                    f"Extracted validity/expiry date '{expiry_val}' (parsed as {parsed_expiry.isoformat()}) "
                    f"is prior to the current date ({today.isoformat()}). "
                    "Reviewer should check whether an updated renewal, lease extension, or NOC has been issued."
                ),
                "document_id": doc.id,
                "page_number": expiry_page,
                "extracted_value": expiry_val,
                "expected_value": f"Validity on or after {today.isoformat()}",
                "evidence": {
                    "field": "expiry_date",
                    "raw_match": expiry_raw,
                    "parsed_date": parsed_expiry.isoformat(),
                    "source_page": expiry_page,
                    "document_filename": doc.original_filename,
                },
            })

    # 4. Intake Reasonableness Check
    if intake_val:
        num_intake = normalize_intake(intake_val)
        if num_intake is not None and (num_intake < 10 or num_intake > 2000):
            findings_to_create.append({
                "rule_code": "INTAKE_RANGE_CHECK",
                "rule_name": "Sanctioned Intake Reasonableness Check",
                "severity": FindingSeverity.INFO,
                "title": f"Out-of-range student intake in '{doc.original_filename}'",
                "detail": (
                    f"Extracted intake value '{intake_val}' ({num_intake} seats) is outside typical illustrative "
                    "programme limits (10 to 2,000 seats). Please review the approved seat allotment."
                ),
                "document_id": doc.id,
                "page_number": intake_page,
                "extracted_value": intake_val,
                "expected_value": "10 to 2000 seats",
                "evidence": {
                    "field": "intake_figure",
                    "parsed_intake": num_intake,
                    "source_page": intake_page,
                    "document_filename": doc.original_filename,
                },
            })

    # 5. Land Area Illustrative Demo Baseline
    if land_val and doc.document_type == "land_deed_lease":
        sq_m, canonical_unit = normalize_land_area(land_val)
        # Demo minimum: 10,000 sq metres (~2.47 acres)
        if sq_m is not None and sq_m < 10000.0:
            findings_to_create.append({
                "rule_code": "LAND_AREA_DEMO_MIN",
                "rule_name": "Land Area Illustrative Baseline Check",
                "severity": FindingSeverity.INFO,
                "title": f"Land area below demo baseline in '{doc.original_filename}'",
                "detail": (
                    f"Extracted land area '{land_val}' (~{sq_m:,.1f} sq m) is below the illustrative demo baseline "
                    "of 10,000 sq m (2.5 acres). Note: This is an illustrative demonstration parameter."
                ),
                "document_id": doc.id,
                "page_number": land_page,
                "extracted_value": land_val,
                "expected_value": ">= 10,000 sq m (demo parameter)",
                "evidence": {
                    "field": "land_area",
                    "sq_metres": sq_m,
                    "source_page": land_page,
                    "is_demo_rule": True,
                    "document_filename": doc.original_filename,
                },
            })

    return findings_to_create


def build_consistency_graph(
    application: Application,
    documents: List[Document],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Perform pairwise cross-document consistency comparisons and construct graph.

    Returns:
      (cross_document_findings, graph_structure)
    """
    cross_findings: List[Dict[str, Any]] = []
    comparisons: List[Dict[str, Any]] = []

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Track processing states and Create Document Nodes in Graph
    unprocessed_docs: List[str] = []
    docs_without_ocr: List[str] = []
    doc_fields_map: Dict[str, Dict[str, Any]] = {}

    for doc in documents:
        if doc.status != DocumentStatus.PROCESSED or doc.extracted_fields is None:
            unprocessed_docs.append(doc.original_filename)
        elif doc.status == DocumentStatus.PROCESSED and not doc.ocr_text:
            docs_without_ocr.append(doc.original_filename)

        doc_node_id = f"doc:{doc.id}"
        nodes.append({
            "id": doc_node_id,
            "type": "document",
            "label": doc.original_filename,
            "metadata": {
                "document_id": doc.id,
                "category": doc.document_type or "other",
                "mime_type": doc.mime_type,
                "status": doc.status.value,
            },
        })

        fields = _parse_extracted_fields(doc)
        doc_fields_map[doc.id] = fields

        # Add Field Nodes & Extraction Edges for all supported comparable fields
        for field_name in ["institution_name", "reference_number", "land_area", "programme_name", "expiry_date", "issue_date"]:
            val, raw, page = _get_field_entry(fields, field_name)
            if val:
                field_node_id = f"field:{doc.id}:{field_name}"
                nodes.append({
                    "id": field_node_id,
                    "type": "field",
                    "label": f"{field_name.replace('_', ' ').title()}: {val}",
                    "metadata": {
                        "field": field_name,
                        "value": val,
                        "raw_match": raw,
                        "page": page,
                        "document_id": doc.id,
                    },
                })
                edges.append({
                    "id": f"edge:extract:{doc.id}:{field_name}",
                    "source": doc_node_id,
                    "target": field_node_id,
                    "type": "extracted_from",
                    "label": f"Page {page}" if page else "Extracted",
                })

    # 2. Pairwise Cross-Document Consistency Checks
    num_docs = len(documents)
    total_matches = 0
    total_discrepancies = 0

    for i in range(num_docs):
        for j in range(i + 1, num_docs):
            doc_a = documents[i]
            doc_b = documents[j]
            fields_a = doc_fields_map.get(doc_a.id, {})
            fields_b = doc_fields_map.get(doc_b.id, {})

            # ── Check A: Institution Name ────────────────────────────────────
            name_a, raw_a, page_a = _get_field_entry(fields_a, "institution_name")
            name_b, raw_b, page_b = _get_field_entry(fields_b, "institution_name")

            if name_a and name_b:
                is_match, expl = are_institution_names_consistent(name_a, name_b)
                comp_status = "match" if is_match else "discrepancy"
                if is_match:
                    total_matches += 1
                    edges.append({
                        "id": f"edge:match:inst:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:institution_name",
                        "target": f"field:{doc_b.id}:institution_name",
                        "type": "consistent",
                        "label": "Matches",
                    })
                else:
                    total_discrepancies += 1
                    edges.append({
                        "id": f"edge:conflict:inst:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:institution_name",
                        "target": f"field:{doc_b.id}:institution_name",
                        "type": "discrepancy",
                        "label": "Conflict",
                    })
                    cross_findings.append({
                        "rule_code": "CROSS_INSTITUTION_NAME_CHECK",
                        "rule_name": "Cross-Document Institution Name Consistency",
                        "severity": FindingSeverity.WARNING,
                        "title": f"Institution name discrepancy between '{doc_a.original_filename}' and '{doc_b.original_filename}'",
                        "detail": expl or f"Name '{name_a}' conflicts with '{name_b}'.",
                        "document_id": None,
                        "page_number": None,
                        "extracted_value": f"Doc A: {name_a} | Doc B: {name_b}",
                        "expected_value": "Consistent institutional title across documents",
                        "evidence": {
                            "field": "institution_name",
                            "doc_a": {"id": doc_a.id, "filename": doc_a.original_filename, "value": name_a, "raw_match": raw_a, "page": page_a},
                            "doc_b": {"id": doc_b.id, "filename": doc_b.original_filename, "value": name_b, "raw_match": raw_b, "page": page_b},
                            "explanation": expl,
                        },
                    })

                comparisons.append({
                    "field": "institution_name",
                    "status": comp_status,
                    "doc_a_id": doc_a.id,
                    "doc_a_name": doc_a.original_filename,
                    "doc_a_value": name_a,
                    "doc_a_page": page_a,
                    "doc_b_id": doc_b.id,
                    "doc_b_name": doc_b.original_filename,
                    "doc_b_value": name_b,
                    "doc_b_page": page_b,
                    "explanation": expl or "Institution names match across both documents.",
                    "severity": "warning" if not is_match else "info",
                })

            # ── Check B: Land Area Consistency ──────────────────────────────
            area_a, raw_area_a, page_area_a = _get_field_entry(fields_a, "land_area")
            area_b, raw_area_b, page_area_b = _get_field_entry(fields_b, "land_area")

            if area_a and area_b:
                is_match, expl = are_areas_consistent(area_a, area_b)
                comp_status = "match" if is_match else "discrepancy"
                if is_match:
                    total_matches += 1
                    edges.append({
                        "id": f"edge:match:area:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:land_area",
                        "target": f"field:{doc_b.id}:land_area",
                        "type": "consistent",
                        "label": "Matches",
                    })
                else:
                    total_discrepancies += 1
                    edges.append({
                        "id": f"edge:conflict:area:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:land_area",
                        "target": f"field:{doc_b.id}:land_area",
                        "type": "discrepancy",
                        "label": "Discrepancy",
                    })
                    cross_findings.append({
                        "rule_code": "CROSS_LAND_AREA_CHECK",
                        "rule_name": "Cross-Document Land Area Consistency",
                        "severity": FindingSeverity.WARNING,
                        "title": f"Land area discrepancy between '{doc_a.original_filename}' and '{doc_b.original_filename}'",
                        "detail": expl or f"Area '{area_a}' contradicts '{area_b}'.",
                        "document_id": None,
                        "page_number": None,
                        "extracted_value": f"Doc A: {area_a} | Doc B: {area_b}",
                        "expected_value": "Consistent land / built-up area across documents",
                        "evidence": {
                            "field": "land_area",
                            "doc_a": {"id": doc_a.id, "filename": doc_a.original_filename, "value": area_a, "raw_match": raw_area_a, "page": page_area_a},
                            "doc_b": {"id": doc_b.id, "filename": doc_b.original_filename, "value": area_b, "raw_match": raw_area_b, "page": page_area_b},
                            "explanation": expl,
                        },
                    })

                comparisons.append({
                    "field": "land_area",
                    "status": comp_status,
                    "doc_a_id": doc_a.id,
                    "doc_a_name": doc_a.original_filename,
                    "doc_a_value": area_a,
                    "doc_a_page": page_area_a,
                    "doc_b_id": doc_b.id,
                    "doc_b_name": doc_b.original_filename,
                    "doc_b_value": area_b,
                    "doc_b_page": page_area_b,
                    "explanation": expl or "Normalized land area figures are consistent.",
                    "severity": "warning" if not is_match else "info",
                })

            # ── Check C: Programme Name Consistency ─────────────────────────
            prog_a, raw_prog_a, page_prog_a = _get_field_entry(fields_a, "programme_name")
            prog_b, raw_prog_b, page_prog_b = _get_field_entry(fields_b, "programme_name")

            if prog_a and prog_b:
                is_match, expl = are_programmes_consistent(prog_a, prog_b)
                comp_status = "match" if is_match else "discrepancy"
                if is_match:
                    total_matches += 1
                else:
                    total_discrepancies += 1
                    cross_findings.append({
                        "rule_code": "CROSS_PROGRAMME_CHECK",
                        "rule_name": "Cross-Document Programme Consistency",
                        "severity": FindingSeverity.WARNING,
                        "title": f"Programme mismatch between '{doc_a.original_filename}' and '{doc_b.original_filename}'",
                        "detail": expl or f"Programme '{prog_a}' conflicts with '{prog_b}'.",
                        "document_id": None,
                        "page_number": None,
                        "extracted_value": f"Doc A: {prog_a} | Doc B: {prog_b}",
                        "expected_value": "Matching programme title across approval documents",
                        "evidence": {
                            "field": "programme_name",
                            "doc_a": {"id": doc_a.id, "filename": doc_a.original_filename, "value": prog_a, "raw_match": raw_prog_a, "page": page_prog_a},
                            "doc_b": {"id": doc_b.id, "filename": doc_b.original_filename, "value": prog_b, "raw_match": raw_prog_b, "page": page_prog_b},
                            "explanation": expl,
                        },
                    })

                comparisons.append({
                    "field": "programme_name",
                    "status": comp_status,
                    "doc_a_id": doc_a.id,
                    "doc_a_name": doc_a.original_filename,
                    "doc_a_value": prog_a,
                    "doc_a_page": page_prog_a,
                    "doc_b_id": doc_b.id,
                    "doc_b_name": doc_b.original_filename,
                    "doc_b_value": prog_b,
                    "doc_b_page": page_prog_b,
                    "explanation": expl or "Programme titles match.",
                    "severity": "warning" if not is_match else "info",
                })

            # ── Check D: Reference Number Consistency ────────────────────────
            ref_a, raw_ref_a, page_ref_a = _get_field_entry(fields_a, "reference_number")
            ref_b, raw_ref_b, page_ref_b = _get_field_entry(fields_b, "reference_number")

            if ref_a and ref_b:
                is_match, expl = are_reference_numbers_consistent(ref_a, ref_b)
                comp_status = "match" if is_match else "discrepancy"
                if is_match:
                    total_matches += 1
                    edges.append({
                        "id": f"edge:match:ref:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:reference_number",
                        "target": f"field:{doc_b.id}:reference_number",
                        "type": "consistent",
                        "label": "Matches",
                    })
                else:
                    total_discrepancies += 1
                    edges.append({
                        "id": f"edge:conflict:ref:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:reference_number",
                        "target": f"field:{doc_b.id}:reference_number",
                        "type": "discrepancy",
                        "label": "Conflict",
                    })
                    cross_findings.append({
                        "rule_code": "CROSS_REFERENCE_NO_CHECK",
                        "rule_name": "Cross-Document Reference Number Consistency",
                        "severity": FindingSeverity.INFO,
                        "title": f"Document reference number mismatch between '{doc_a.original_filename}' and '{doc_b.original_filename}'",
                        "detail": expl or f"Reference '{ref_a}' conflicts with '{ref_b}'.",
                        "document_id": None,
                        "page_number": None,
                        "extracted_value": f"Doc A: {ref_a} | Doc B: {ref_b}",
                        "expected_value": "Consistent reference or order identifier across documents",
                        "evidence": {
                            "field": "reference_number",
                            "doc_a": {"id": doc_a.id, "filename": doc_a.original_filename, "value": ref_a, "raw_match": raw_ref_a, "page": page_ref_a},
                            "doc_b": {"id": doc_b.id, "filename": doc_b.original_filename, "value": ref_b, "raw_match": raw_ref_b, "page": page_ref_b},
                            "explanation": expl,
                        },
                    })

                comparisons.append({
                    "field": "reference_number",
                    "status": comp_status,
                    "doc_a_id": doc_a.id,
                    "doc_a_name": doc_a.original_filename,
                    "doc_a_value": ref_a,
                    "doc_a_page": page_ref_a,
                    "doc_b_id": doc_b.id,
                    "doc_b_name": doc_b.original_filename,
                    "doc_b_value": ref_b,
                    "doc_b_page": page_ref_b,
                    "explanation": expl or "Document reference numbers match across both documents.",
                    "severity": "info",
                })

            # ── Check E: Expiry Date Consistency ─────────────────────────────
            exp_a, raw_exp_a, page_exp_a = _get_field_entry(fields_a, "expiry_date")
            exp_b, raw_exp_b, page_exp_b = _get_field_entry(fields_b, "expiry_date")

            if exp_a and exp_b:
                is_match, expl = are_dates_consistent(exp_a, exp_b)
                comp_status = "match" if is_match else "discrepancy"
                if is_match:
                    total_matches += 1
                    edges.append({
                        "id": f"edge:match:exp:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:expiry_date",
                        "target": f"field:{doc_b.id}:expiry_date",
                        "type": "consistent",
                        "label": "Matches",
                    })
                else:
                    total_discrepancies += 1
                    edges.append({
                        "id": f"edge:conflict:exp:{doc_a.id}:{doc_b.id}",
                        "source": f"field:{doc_a.id}:expiry_date",
                        "target": f"field:{doc_b.id}:expiry_date",
                        "type": "discrepancy",
                        "label": "Conflict",
                    })
                    cross_findings.append({
                        "rule_code": "CROSS_EXPIRY_DATE_CHECK",
                        "rule_name": "Cross-Document Expiry Date Consistency",
                        "severity": FindingSeverity.WARNING,
                        "title": f"Document expiry date discrepancy between '{doc_a.original_filename}' and '{doc_b.original_filename}'",
                        "detail": expl or f"Expiry date '{exp_a}' conflicts with '{exp_b}'.",
                        "document_id": None,
                        "page_number": None,
                        "extracted_value": f"Doc A: {exp_a} | Doc B: {exp_b}",
                        "expected_value": "Consistent expiry or validity date across approval documents",
                        "evidence": {
                            "field": "expiry_date",
                            "doc_a": {"id": doc_a.id, "filename": doc_a.original_filename, "value": exp_a, "raw_match": raw_exp_a, "page": page_exp_a},
                            "doc_b": {"id": doc_b.id, "filename": doc_b.original_filename, "value": exp_b, "raw_match": raw_exp_b, "page": page_exp_b},
                            "explanation": expl,
                        },
                    })

                comparisons.append({
                    "field": "expiry_date",
                    "status": comp_status,
                    "doc_a_id": doc_a.id,
                    "doc_a_name": doc_a.original_filename,
                    "doc_a_value": exp_a,
                    "doc_a_page": page_exp_a,
                    "doc_b_id": doc_b.id,
                    "doc_b_name": doc_b.original_filename,
                    "doc_b_value": exp_b,
                    "doc_b_page": page_exp_b,
                    "explanation": expl or "Document expiry dates match across both documents.",
                    "severity": "warning" if not is_match else "info",
                })

    field_nodes_count = len([n for n in nodes if n["type"] == "field"])
    has_comparable_fields = len(comparisons) > 0

    if num_docs < 2:
        explanation = "At least 2 uploaded documents are required to form a cross-document consistency graph."
    elif not has_comparable_fields:
        if unprocessed_docs:
            explanation = (
                f"No comparable extracted fields available. {len(unprocessed_docs)} document(s) have not undergone "
                f"OCR and field extraction ({', '.join(unprocessed_docs)}). Run extraction on uploaded documents to discover comparable metadata."
            )
        elif docs_without_ocr and field_nodes_count == 0:
            explanation = (
                f"No comparable extracted fields available. Extracted text was empty for {len(docs_without_ocr)} document(s) "
                f"({', '.join(docs_without_ocr)}). If these are scanned image files, install Tesseract OCR on the host system."
            )
        elif field_nodes_count == 0:
            explanation = (
                "No comparable extracted fields available. Documents have been ingested, but no structured institutional metadata "
                "(institution name, reference number, land area, programme, dates) was detected in the document text."
            )
        else:
            explanation = (
                "No comparable extracted fields available across evaluated document pairs. Discovered fields do not overlap "
                "across documents to perform pairwise cross-referencing."
            )
    else:
        explanation = None

    graph_data = {
        "application_id": application.id,
        "nodes": nodes,
        "edges": edges,
        "comparisons": comparisons,
        "total_matches": total_matches,
        "total_discrepancies": total_discrepancies,
        "evaluated_pairs": len(comparisons),
        "has_comparable_fields": has_comparable_fields,
        "explanation": explanation,
        "unprocessed_documents": unprocessed_docs,
    }

    return (cross_findings, graph_data)


def run_application_validation(
    db: Session,
    application_id: str,
    actor_label: str = "system",
) -> Tuple[List[Finding], Dict[str, Any]]:
    """Execute complete validation suite on an application.

    1. Gathers documents and automatically triggers extraction for pending documents.
    2. Runs single-document checks.
    3. Runs cross-document consistency checks and builds the graph.
    4. Idempotently persists findings without duplicating existing or resolved items.
    5. Logs an audit trail event.
    """
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise ValueError(f"Application '{application_id}' not found.")

    docs = db.execute(
        select(Document).where(Document.application_id == application_id)
    ).scalars().all()

    # Automatically trigger extraction for documents that have not yet been processed
    try:
        from app.core.config import get_settings
        from app.services.processing_service import process_document
        from app.services.storage.local import LocalStorageBackend

        settings = get_settings()
        storage = LocalStorageBackend(settings.upload_dir)
        processed_any = False
        for doc in docs:
            if doc.status == DocumentStatus.UPLOADED and not doc.extracted_fields:
                try:
                    process_document(
                        db=db,
                        doc=doc,
                        storage=storage,
                        tesseract_cmd=settings.tesseract_cmd,
                        actor_label=actor_label,
                    )
                    processed_any = True
                except Exception as proc_exc:
                    logger.warning("Auto-processing during validation skipped document %s: %s", doc.id, proc_exc)
        if processed_any:
            docs = db.execute(
                select(Document).where(Document.application_id == application_id)
            ).scalars().all()
    except Exception as auto_exc:
        logger.warning("Auto-processing check failed during validation: %s", auto_exc)


    # Collect single-document findings
    candidate_findings: List[Dict[str, Any]] = []
    for doc in docs:
        candidate_findings.extend(evaluate_document_rules(doc))

    # Collect cross-document consistency findings & graph
    cross_findings, graph_data = build_consistency_graph(app, list(docs))
    candidate_findings.extend(cross_findings)

    # Fetch existing findings for this application
    existing_findings = db.execute(
        select(Finding).where(Finding.application_id == application_id)
    ).scalars().all()

    # Map existing findings by unique deduplication key
    # Key: (rule_code, document_id, evidence_field, doc_a_id, doc_b_id)
    def _finding_key(item: Any) -> Tuple:
        ev = item.evidence if isinstance(item, Finding) else item.get("evidence", {})
        doc_id = item.document_id if isinstance(item, Finding) else item.get("document_id")
        rule_code = item.rule_code if isinstance(item, Finding) else item.get("rule_code")
        field = ev.get("field") if ev else None
        doc_a_id = ev.get("doc_a", {}).get("id") if ev and "doc_a" in ev else None
        doc_b_id = ev.get("doc_b", {}).get("id") if ev and "doc_b" in ev else None
        return (rule_code, doc_id, field, doc_a_id, doc_b_id)

    existing_map = {_finding_key(f): f for f in existing_findings}

    persisted_findings: List[Finding] = []
    created_count = 0
    updated_count = 0

    for candidate in candidate_findings:
        key = _finding_key(candidate)
        existing = existing_map.get(key)

        if existing:
            # If finding was already reviewed/resolved by officer, preserve reviewer status & notes!
            if existing.status in (FindingStatus.RESOLVED, FindingStatus.DISMISSED, FindingStatus.UNDER_REVIEW, FindingStatus.REQUIRES_CLARIFICATION):
                persisted_findings.append(existing)
                continue

            # Update OPEN finding details
            existing.detail = candidate["detail"]
            existing.extracted_value = candidate["extracted_value"]
            existing.expected_value = candidate["expected_value"]
            existing.evidence = candidate["evidence"]
            existing.page_number = candidate.get("page_number")
            persisted_findings.append(existing)
            updated_count += 1
        else:
            new_finding = Finding(
                application_id=application_id,
                document_id=candidate.get("document_id"),
                rule_code=candidate["rule_code"],
                rule_name=candidate["rule_name"],
                severity=candidate["severity"],
                status=FindingStatus.OPEN,
                title=candidate["title"],
                detail=candidate["detail"],
                page_number=candidate.get("page_number"),
                extracted_value=candidate.get("extracted_value"),
                expected_value=candidate.get("expected_value"),
                evidence=candidate.get("evidence"),
            )
            db.add(new_finding)
            persisted_findings.append(new_finding)
            created_count += 1

    # Record Audit Event
    audit = AuditEvent(
        application_id=application_id,
        actor_label=actor_label,
        action="application.validated",
        resource_type="application",
        resource_id=application_id,
        detail=(
            f"Validation run completed: {len(candidate_findings)} total observations "
            f"({created_count} created, {updated_count} refreshed, {graph_data['total_discrepancies']} discrepancies)."
        ),
        metadata_={
            "created_count": created_count,
            "updated_count": updated_count,
            "total_matches": graph_data["total_matches"],
            "total_discrepancies": graph_data["total_discrepancies"],
        },
    )
    db.add(audit)
    db.commit()

    # Re-query all current findings for this application
    all_findings = db.execute(
        select(Finding)
        .where(Finding.application_id == application_id)
        .order_by(Finding.created_at.desc())
    ).scalars().all()

    logger.info(
        "Validation complete for application %s: %d findings recorded",
        application_id, len(all_findings),
    )

    return (list(all_findings), graph_data)
