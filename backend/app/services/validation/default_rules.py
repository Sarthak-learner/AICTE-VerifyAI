"""Configurable default validation rules for AICTE VerifyAI.

All threshold values here are illustrative demo values and are explicitly
flagged as is_demo=True. They do not constitute official AICTE regulations.
"""
from typing import Any, Dict, List

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "code": "REQ_INSTITUTION_NAME",
        "name": "Institution Name Presence",
        "description": "Verifies that an institutional name was detected in document text.",
        "applies_to_document_type": None,
        "severity": "warning",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "institution_name"},
    },
    {
        "code": "REQ_REFERENCE_NO",
        "name": "Reference Number Presence",
        "description": "Checks for a detectable file, order, or application reference number.",
        "applies_to_document_type": None,
        "severity": "info",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "reference_number"},
    },
    {
        "code": "DOC_EXPIRY_CHECK",
        "name": "Document Validity & Expiry",
        "description": "Checks whether an extracted document validity or expiry date is in the past.",
        "applies_to_document_type": None,
        "severity": "warning",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "expiry_date"},
    },
    {
        "code": "INTAKE_RANGE_CHECK",
        "name": "Sanctioned Intake Reasonableness",
        "description": "Checks whether the student intake number falls within standard illustrative limits (10 to 2000).",
        "applies_to_document_type": None,
        "severity": "info",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "intake_figure", "min_intake": 10, "max_intake": 2000},
    },
    {
        "code": "LAND_AREA_DEMO_MIN",
        "name": "Land Area Illustrative Baseline",
        "description": "Checks if extracted land area meets illustrative demo baseline (minimum 2.5 acres / ~10,000 sq m).",
        "applies_to_document_type": "land_deed_lease",
        "severity": "info",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "land_area", "min_sq_metres": 10000.0},
    },
    # Cross-document rules
    {
        "code": "CROSS_INSTITUTION_NAME_CHECK",
        "name": "Cross-Document Institution Name Consistency",
        "description": "Identifies discrepancies in institution names between different uploaded documents.",
        "applies_to_document_type": None,
        "severity": "warning",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "institution_name"},
    },
    {
        "code": "CROSS_LAND_AREA_CHECK",
        "name": "Cross-Document Land Area Consistency",
        "description": "Identifies numerical discrepancies in land or built-up area across different documents.",
        "applies_to_document_type": None,
        "severity": "warning",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "land_area", "tolerance_pct": 0.08},
    },
    {
        "code": "CROSS_PROGRAMME_CHECK",
        "name": "Cross-Document Programme Consistency",
        "description": "Identifies conflicting programme or course titles across supporting documents.",
        "applies_to_document_type": None,
        "severity": "warning",
        "is_active": True,
        "is_demo": True,
        "parameters": {"field": "programme_name"},
    },
]
