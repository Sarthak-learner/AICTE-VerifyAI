"""Pydantic schemas for Application resources."""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.application import ApplicationStatus

# ── Allowed values ────────────────────────────────────────────────────────────

APPLICATION_CATEGORIES = [
    "new_institution",
    "new_programme",
    "additional_intake",
    "extension_of_approval",
    "closure",
    "other",
]

PROGRAMME_TYPES = [
    "BE_BTech",
    "ME_MTech",
    "MBA",
    "MCA",
    "BCA",
    "Diploma",
    "PhD",
    "other",
]

ACADEMIC_YEAR_PATTERN = re.compile(r"^\d{4}-\d{2}$")  # e.g. 2025-26


# ── Request schemas ───────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    institution_name: str = Field(..., min_length=2, max_length=512,
                                  description="Full legal name of the institution")
    aicte_permanent_id: Optional[str] = Field(
        None, max_length=64,
        description="AICTE Permanent ID or synthetic demo identifier"
    )
    academic_year: str = Field(..., description="Academic year, e.g. 2025-26")
    application_category: str = Field(..., description="Category of this application")
    programme_type: str = Field(..., description="Programme / course type")
    description: Optional[str] = Field(None, max_length=2000,
                                       description="Free-text description or notes")
    applicant_name: str = Field(..., min_length=2, max_length=255,
                                description="Name of the primary contact / applicant")
    applicant_email: str = Field(..., max_length=255,
                                 description="Contact e-mail address")

    @field_validator("academic_year")
    @classmethod
    def validate_academic_year(cls, v: str) -> str:
        if not ACADEMIC_YEAR_PATTERN.match(v):
            raise ValueError(
                "academic_year must be in YYYY-YY format, e.g. 2025-26"
            )
        return v

    @field_validator("application_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in APPLICATION_CATEGORIES:
            raise ValueError(
                f"application_category must be one of: {APPLICATION_CATEGORIES}"
            )
        return v

    @field_validator("programme_type")
    @classmethod
    def validate_programme_type(cls, v: str) -> str:
        if v not in PROGRAMME_TYPES:
            raise ValueError(
                f"programme_type must be one of: {PROGRAMME_TYPES}"
            )
        return v

    @field_validator("applicant_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("applicant_email must be a valid e-mail address")
        return v.lower().strip()


# ── Response schemas ──────────────────────────────────────────────────────────

class ApplicationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    reference_number: str
    institution_name: str
    aicte_permanent_id: Optional[str]
    academic_year: str
    application_category: str
    programme_type: str
    description: Optional[str]
    applicant_name: str
    applicant_email: str
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class ApplicationListItem(BaseModel):
    """Lightweight summary for list view."""
    model_config = {"from_attributes": True}

    id: str
    reference_number: str
    institution_name: str
    academic_year: str
    application_category: str
    status: ApplicationStatus
    created_at: datetime


class ApplicationList(BaseModel):
    total: int
    items: list[ApplicationListItem]


class AuditEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    application_id: Optional[str] = None
    actor_label: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime


class AuditTrailResponse(BaseModel):
    application_id: Optional[str] = None
    total: int
    events: list[AuditEventResponse]

