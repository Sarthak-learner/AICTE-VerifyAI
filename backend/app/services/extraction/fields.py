"""Deterministic structured field extraction from OCR text.

Extracts the following fields where detectable:
  - institution_name       : institution or organisation name
  - reference_number       : document/application reference number
  - issue_date             : date the document was issued
  - expiry_date            : validity/expiry date
  - land_area              : land area with unit (e.g. "5 acres", "2000 sq m")
  - programme_name         : programme or course name
  - intake_figure          : sanctioned/proposed student intake

Rules:
  - A field that cannot be reliably extracted is returned as null (None).
  - Fields are never fabricated. Patterns must match real extracted text.
  - The original span text is preserved as evidence.
  - This is NOT regulatory validation — these are advisory observations only.
"""
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Regex patterns ────────────────────────────────────────────────────────────

# Date variants: "22 October 2025", "22/10/2025", "2025-10-22", "Oct 22, 2025"
_DATE_PATTERN = re.compile(
    r"""
    (?:                                           # Full word-month variant
        (?:0?[1-9]|[12]\d|3[01])               # day
        [\s/-]
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        [\s,-]+
        (?:19|20)\d{2}                           # year
    )
    |
    (?:                                           # Numeric variants
        (?:0?[1-9]|[12]\d|3[01])
        [/\-\.]
        (?:0?[1-9]|1[0-2])
        [/\-\.]
        (?:19|20)\d{2}
    )
    |
    (?:                                           # ISO 8601
        (?:19|20)\d{2}
        -
        (?:0?[1-9]|1[0-2])
        -
        (?:0?[1-9]|[12]\d|3[01])
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Reference numbers: e.g. "F.No. 123/2025", "Ref: ABC-001", "APP-2025-XXXX"
_REF_PATTERN = re.compile(
    r"(?:Ref(?:erence)?\.?(?:\s*No\.?|\s*Number|\s*#)?|F\.?\s*No\.?|Order\s+No\.?|Letter\s+No\.?|File\s+No\.?)"
    r"\s*[:.\-]?\s*(?:F\.?\s*No\.?\s*[:.]?\s*)?([a-zA-Z0-9][\w/\-\.]{3,40})",
    re.IGNORECASE,
)

# Land area: "5 acres", "2000 sq m", "1.5 hectares", "5000 sq.ft"
_LAND_AREA_PATTERN = re.compile(
    r"""
    (
        \d+(?:[.,]\d+)?                           # numeric value
        \s*
        (?:
            sq\.?\s*(?:m(?:eters?)?|ft|feet|yard|yd)
            | acres?
            | hectares?
            | guntha
            | bigha
            | sq\.?\s*km
        )
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Intake: "100 seats", "Intake: 60", "sanctioned intake of 120"
_INTAKE_PATTERN = re.compile(
    r"""
    (?:
        intake\s*(?:of\s*)?
        |sanctioned\s+intake\s*(?:of\s*)?
        |approved\s+intake\s*(?:of\s*)?
        |student\s+strength\s*(?:of\s*)?
        |seats?\s*[=:]\s*
        |\bseats?\s+
    )
    (\d{2,4})
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Programme name: "B.E. / B.Tech in Computer Science", "MBA (Marketing)"
_PROGRAMME_PATTERN = re.compile(
    r"""
    (?:programme|course|branch|stream|discipline)\s*[:\-]?\s*
    (
        [A-Z][^\n\.]{5,80}
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Institution name: look for known indicators
_INSTITUTION_PATTERN = re.compile(
    r"""
    (?:
        (?:Name\s+of\s+(?:the\s+)?(?:institution|college|university|institute|school))
        |(?:institution\s+name)
        |(?:college\s+name)
    )
    \s*[:\-]?\s*
    (.+?)
    (?:\n|$)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Issue / validity keywords for date disambiguation
_ISSUE_KEYWORDS = re.compile(
    r"(?:issue[d]?\s+on|dated?|date\s+of\s+issue)", re.IGNORECASE
)
_EXPIRY_KEYWORDS = re.compile(
    r"(?:valid\s+(?:up\s+to|till|until)|expir(?:y|es?|ation)|validity\s+date)", re.IGNORECASE
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ExtractedField:
    value: Optional[str]
    raw_match: Optional[str]     # The exact text span that produced the value
    source_page: Optional[int]   # Page number (1-indexed) where it was found
    confidence: str              # "high" | "low" | "unknown"


@dataclass
class ExtractedFields:
    institution_name: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    reference_number: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    issue_date: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    expiry_date: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    land_area: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    programme_name: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))
    intake_figure: ExtractedField = field(default_factory=lambda: ExtractedField(None, None, None, "unknown"))

    def to_json(self) -> str:
        """Serialize to JSON for database storage."""
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, raw: str) -> "ExtractedFields":
        """Deserialize from JSON string."""
        try:
            data = json.loads(raw)
            fields = {}
            for f_name in [
                "institution_name", "reference_number", "issue_date",
                "expiry_date", "land_area", "programme_name", "intake_figure"
            ]:
                f_data = data.get(f_name, {}) or {}
                fields[f_name] = ExtractedField(
                    value=f_data.get("value"),
                    raw_match=f_data.get("raw_match"),
                    source_page=f_data.get("source_page"),
                    confidence=f_data.get("confidence", "unknown"),
                )
            return cls(**fields)
        except Exception:
            return cls()


# ── Extraction logic ──────────────────────────────────────────────────────────

def _first_match(pattern: re.Pattern, text: str, group: int = 0) -> Optional[str]:
    m = pattern.search(text)
    return m.group(group).strip() if m else None


def extract_fields(pages: list[tuple[int, str]]) -> ExtractedFields:
    """Extract structured fields from a list of (page_number, text) tuples.

    Each field is extracted from the first page where it appears.
    Returns ExtractedFields with None values for undetectable fields.

    IMPORTANT: This function does NOT validate extracted values against
    regulatory rules. Fields are advisory only.
    """
    result = ExtractedFields()

    # Concatenated full text (for cross-page patterns)
    all_text = "\n".join(text for _, text in pages)

    for page_num, text in pages:
        # --- Institution name ---
        if result.institution_name.value is None:
            m = _INSTITUTION_PATTERN.search(text)
            if m:
                val = m.group(1).strip()[:255]
                result.institution_name = ExtractedField(
                    value=val, raw_match=m.group(0).strip(), source_page=page_num, confidence="high"
                )

        # --- Reference number ---
        if result.reference_number.value is None:
            m = _REF_PATTERN.search(text)
            if m:
                result.reference_number = ExtractedField(
                    value=m.group(1).strip(), raw_match=m.group(0).strip(),
                    source_page=page_num, confidence="high"
                )

        # --- Issue date & expiry date ---
        # Look for dates near context keywords
        lines = text.split("\n")
        for line in lines:
            date_m = _DATE_PATTERN.search(line)
            if not date_m:
                continue

            date_str = date_m.group(0).strip()

            if result.issue_date.value is None and _ISSUE_KEYWORDS.search(line):
                result.issue_date = ExtractedField(
                    value=date_str, raw_match=line.strip(),
                    source_page=page_num, confidence="high"
                )
            elif result.expiry_date.value is None and _EXPIRY_KEYWORDS.search(line):
                result.expiry_date = ExtractedField(
                    value=date_str, raw_match=line.strip(),
                    source_page=page_num, confidence="high"
                )
            # Fallback: first standalone date as issue_date (low confidence)
            elif result.issue_date.value is None:
                result.issue_date = ExtractedField(
                    value=date_str, raw_match=line.strip(),
                    source_page=page_num, confidence="low"
                )

        # --- Land area ---
        if result.land_area.value is None:
            m = _LAND_AREA_PATTERN.search(text)
            if m:
                result.land_area = ExtractedField(
                    value=m.group(1).strip(), raw_match=m.group(0).strip(),
                    source_page=page_num, confidence="high"
                )

        # --- Programme name ---
        if result.programme_name.value is None:
            m = _PROGRAMME_PATTERN.search(text)
            if m:
                val = m.group(1).strip()[:200]
                result.programme_name = ExtractedField(
                    value=val, raw_match=m.group(0).strip(),
                    source_page=page_num, confidence="high"
                )

        # --- Intake ---
        if result.intake_figure.value is None:
            m = _INTAKE_PATTERN.search(text)
            if m:
                result.intake_figure = ExtractedField(
                    value=m.group(1).strip(), raw_match=m.group(0).strip(),
                    source_page=page_num, confidence="high"
                )

    return result
