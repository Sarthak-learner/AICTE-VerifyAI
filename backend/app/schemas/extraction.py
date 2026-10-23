"""Pydantic schemas for OCR extraction and processing results."""
from typing import Optional, Any
from pydantic import BaseModel

from app.models.document import DocumentStatus


class ExtractedFieldSchema(BaseModel):
    value: Optional[str]
    raw_match: Optional[str]
    source_page: Optional[int]
    confidence: str  # "high" | "low" | "unknown"


class ExtractionResultSchema(BaseModel):
    """Returned by GET /documents/{id}/extraction — advisory, not verified."""
    document_id: str
    status: DocumentStatus
    ocr_text: Optional[str]          # Full extracted text (may be long)
    ocr_text_preview: Optional[str]  # First 500 chars for display
    extracted_fields: Optional[dict[str, Any]]  # Parsed JSON of ExtractedFields
    page_count: Optional[int]
    warning: Optional[str] = None     # e.g. Tesseract unavailable message


class ProcessingStatusResponse(BaseModel):
    """Returned immediately after triggering processing."""
    document_id: str
    status: DocumentStatus
    message: str
