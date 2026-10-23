"""Normalization utilities for robust cross-document field comparison.

Normalizes:
  - Text: lowercase, whitespace collapsed, punctuation stripped, institutional abbreviations.
  - Dates: parsed to standard datetime.date objects for calendar-accurate comparisons.
  - Land Area: converted to square metres with configurable tolerance (e.g. 5% for rounding).
  - Intake figures: parsed to numeric integers.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Tuple

# Common institutional abbreviations to expand for fuzzy consistency
_EXPANSIONS = {
    r"\bengg\b": "engineering",
    r"\btech\b": "technology",
    r"\bpoly\b": "polytechnic",
    r"\binst\b": "institute",
    r"\buniv\b": "university",
    r"\bgovt\b": "government",
    r"\bgov\b": "government",
    r"\bdept\b": "department",
    r"\bcoll\b": "college",
}

# Conversion multipliers to square metres
_AREA_MULTIPLIERS = {
    "acre": 4046.856,
    "acres": 4046.856,
    "hectare": 10000.0,
    "hectares": 10000.0,
    "ha": 10000.0,
    "sq m": 1.0,
    "sq.m": 1.0,
    "sqm": 1.0,
    "sq meter": 1.0,
    "sq meters": 1.0,
    "sq metre": 1.0,
    "sq metres": 1.0,
    "sq ft": 0.092903,
    "sq.ft": 0.092903,
    "sqft": 0.092903,
    "square feet": 0.092903,
    "square foot": 0.092903,
    "bigha": 2529.285,
}

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
]


def normalize_text(text: Optional[str]) -> Optional[str]:
    """Normalize text by collapsing whitespace, lowercasing, and expanding standard abbreviations."""
    if not text:
        return None
    s = text.strip().lower()
    # Replace ampersands with 'and'
    s = s.replace("&", " and ")
    # Expand known abbreviations
    for pattern, replacement in _EXPANSIONS.items():
        s = re.sub(pattern, replacement, s)
    # Remove punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def normalize_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string into a standard datetime.date."""
    if not date_str:
        return None
    clean = re.sub(r"[,\s]+", " ", date_str.strip())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    # Try finding YYYY-MM-DD anywhere in string
    iso_match = re.search(r"\b(19|20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", date_str)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date()
        except ValueError:
            pass
    # Try finding DD/MM/YYYY
    dmy_match = re.search(r"\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19|20\d{2})\b", date_str)
    if dmy_match:
        try:
            return datetime.strptime(dmy_match.group(0), "%d/%m/%Y").date()
        except ValueError:
            pass
    return None


def normalize_land_area(area_str: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """Parse a land area string into (sq_metres, canonical_unit).

    Returns (None, raw_str) if parsing fails.
    """
    if not area_str:
        return (None, None)
    clean = area_str.strip().lower()
    # Match number and unit (e.g. "5.5 acres", "2000 sq m", "15000 sq.ft")
    match = re.search(
        r"([\d]+(?:\.\d+)?)\s*(acres?|hectares?|ha|sq\.?\s*m(?:eters?|etres?)?|sqm|sq\.?\s*ft|sqft|square\s+feet|bigha)",
        clean,
    )
    if not match:
        return (None, area_str)

    val_str, unit_str = match.groups()
    try:
        val = float(val_str)
    except ValueError:
        return (None, area_str)

    # Normalize unit key
    unit_key = re.sub(r"\s+", " ", unit_str).strip()
    multiplier = _AREA_MULTIPLIERS.get(unit_key)
    if multiplier is None:
        return (None, area_str)

    sq_metres = val * multiplier
    return (sq_metres, unit_key)


def are_areas_consistent(
    area1: Optional[str],
    area2: Optional[str],
    tolerance_pct: float = 0.08,
) -> Tuple[bool, Optional[str]]:
    """Compare two land area strings.

    Returns (is_consistent, explanation_if_discrepancy).
    If both convert to square metres, allows tolerance_pct (default 8% for survey rounding).
    """
    if not area1 or not area2:
        return (True, None)

    sqm1, _ = normalize_land_area(area1)
    sqm2, _ = normalize_land_area(area2)

    if sqm1 is not None and sqm2 is not None:
        max_val = max(sqm1, sqm2)
        if max_val == 0:
            return (True, None)
        diff_pct = abs(sqm1 - sqm2) / max_val
        if diff_pct <= tolerance_pct:
            return (True, None)
        return (
            False,
            f"Extracted land area '{area1}' (~{sqm1:,.1f} sq m) contradicts '{area2}' (~{sqm2:,.1f} sq m) beyond {int(tolerance_pct*100)}% tolerance.",
        )

    # Fallback to textual match if unit is unrecognized
    norm1 = normalize_text(area1)
    norm2 = normalize_text(area2)
    if norm1 == norm2:
        return (True, None)
    return (
        False,
        f"Extracted area figures '{area1}' and '{area2}' do not match.",
    )


def are_institution_names_consistent(
    name1: Optional[str],
    name2: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Compare two institution names using normalized token sets."""
    if not name1 or not name2:
        return (True, None)

    norm1 = normalize_text(name1)
    norm2 = normalize_text(name2)
    if not norm1 or not norm2:
        return (True, None)

    if norm1 == norm2:
        return (True, None)

    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return (True, None)

    # Check Jaccard word similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    similarity = len(intersection) / len(union)

    # If high overlap (> 0.70) or one is a subset of the other (e.g. city added at end)
    if similarity >= 0.70 or words1.issubset(words2) or words2.issubset(words1):
        return (True, None)

    return (
        False,
        f"Institution name '{name1}' differs significantly from '{name2}'.",
    )


def are_programmes_consistent(
    prog1: Optional[str],
    prog2: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Compare two programme/course names."""
    if not prog1 or not prog2:
        return (True, None)

    norm1 = normalize_text(prog1)
    norm2 = normalize_text(prog2)
    if not norm1 or not norm2:
        return (True, None)

    if norm1 == norm2:
        return (True, None)

    words1 = set(norm1.split())
    words2 = set(norm2.split())
    intersection = words1.intersection(words2)
    if len(intersection) >= min(len(words1), len(words2)):
        return (True, None)

    return (
        False,
        f"Programme '{prog1}' conflicts with '{prog2}'.",
    )


def normalize_intake(intake_str: Optional[str]) -> Optional[int]:
    """Parse an intake figure to a clean integer."""
    if not intake_str:
        return None
    match = re.search(r"\b(\d{1,5})\b", intake_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def normalize_reference_number(ref_str: Optional[str]) -> Optional[str]:
    """Normalize a reference/order/letter number by stripping labels and special punctuation."""
    if not ref_str:
        return None
    s = ref_str.strip().lower()
    # Strip common prefix keywords
    s = re.sub(
        r"^(?:f\.?\s*no\.?|ref(?:erence)?\.?(?:\s*no\.?|\s*number|\s*#)?|order\s+no\.?|letter\s+no\.?|file\s+no\.?|app\s*(?:no\.?|id)?)\s*[:.]?\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Normalize whitespace/separators to dash
    s = re.sub(r"[\s_/\-]+", "-", s)
    s = re.sub(r"[^\w\-]", "", s).strip("-")
    return s if s else None


def are_reference_numbers_consistent(
    ref1: Optional[str],
    ref2: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Compare two reference or order numbers."""
    if not ref1 or not ref2:
        return (True, None)

    norm1 = normalize_reference_number(ref1)
    norm2 = normalize_reference_number(ref2)
    if not norm1 or not norm2:
        return (True, None)

    if norm1 == norm2:
        return (True, None)

    return (
        False,
        f"Document reference number '{ref1}' differs from '{ref2}'.",
    )


def are_dates_consistent(
    date1: Optional[str],
    date2: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Compare two date strings after calendar normalization."""
    if not date1 or not date2:
        return (True, None)

    d1 = normalize_date(date1)
    d2 = normalize_date(date2)

    if d1 is not None and d2 is not None:
        if d1 == d2:
            return (True, None)
        return (
            False,
            f"Date '{date1}' ({d1.isoformat()}) contradicts '{date2}' ({d2.isoformat()}).",
        )

    norm1 = normalize_text(date1)
    norm2 = normalize_text(date2)
    if norm1 and norm2 and norm1 == norm2:
        return (True, None)

    return (
        False,
        f"Date '{date1}' does not match '{date2}'.",
    )

