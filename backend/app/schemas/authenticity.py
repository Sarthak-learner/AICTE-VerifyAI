"""Pydantic schemas for document authenticity screening."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.authenticity import AuthenticityResult
from app.models.finding import FindingStatus


class AuthenticityCheckResponse(BaseModel):
    id: str
    application_id: str
    document_id: str
    document_filename: Optional[str] = None
    document_type: Optional[str] = None
    check_type: str
    check_name: str
    result: AuthenticityResult
    explanation: str
    evidence: Optional[Dict[str, Any]] = None
    screening_version: str
    reviewer_status: FindingStatus
    reviewer_notes: Optional[str] = None
    resolved_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthenticityCheckUpdatePayload(BaseModel):
    reviewer_status: FindingStatus = Field(
        ...,
        description="Updated status: open, under_review, resolved, dismissed, or requires_clarification",
    )
    reviewer_notes: Optional[str] = Field(
        None,
        description="Reviewer rationale or verification notes",
    )
    reviewer_label: Optional[str] = Field(
        None,
        description="Reviewer identifier or name for audit logging",
    )


class DocumentAuthenticityGroup(BaseModel):
    document_id: str
    document_filename: str
    document_type: Optional[str] = None
    checks: List[AuthenticityCheckResponse]
    pass_count: int
    review_count: int
    unavailable_count: int


class AuthenticityScreeningResponse(BaseModel):
    application_id: str
    total_checks: int
    total_passed: int
    total_review_required: int
    total_unavailable: int
    documents: List[DocumentAuthenticityGroup]
    checks: List[AuthenticityCheckResponse]
    message: str
    disclaimer: str = (
        "Authenticity screening identifies suspicious indicators for manual human review. "
        "Flags are review triggers, NOT proof of forgery or manipulation. "
        "Absence of flags does not constitute official certification."
    )
