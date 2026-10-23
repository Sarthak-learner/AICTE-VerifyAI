"""Pydantic schemas for Document resources."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus

# ── Document categories ───────────────────────────────────────────────────────

DOCUMENT_CATEGORIES = [
    "application_form",
    "land_deed_lease",
    "building_plan",
    "faculty_list",
    "affidavit",
    "noc_certificate",
    "other",
]


# ── Response schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Full document metadata — never includes storage path or file content."""
    model_config = {"from_attributes": True}

    id: str
    application_id: str
    original_filename: str
    document_type: Optional[str]
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    page_count: Optional[int]
    status: DocumentStatus
    is_duplicate: bool
    duplicate_of_id: Optional[str]
    created_at: datetime


class DocumentListItem(BaseModel):
    """Lightweight summary for list view."""
    model_config = {"from_attributes": True}

    id: str
    application_id: str
    original_filename: str
    document_type: Optional[str]
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    is_duplicate: bool
    created_at: datetime


class DocumentList(BaseModel):
    total: int
    items: list[DocumentListItem]


class DuplicateInfo(BaseModel):
    """Returned alongside a DocumentResponse when a duplicate is detected."""
    existing_document_id: str
    existing_application_id: str
    message: str


class UploadResponse(BaseModel):
    """Response after a successful (or duplicate-flagged) upload."""
    document: DocumentResponse
    duplicate: Optional[DuplicateInfo] = None
