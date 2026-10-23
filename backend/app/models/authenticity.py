"""Authenticity check records for document verification.

Stores deterministic screening results (hash integrity, PDF metadata,
PDF structure, image indicators, text consistency, digital signature presence)
and reviewer status/resolution notes.
"""
from __future__ import annotations

import enum
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid
from app.models.finding import FindingStatus


class AuthenticityResult(str, enum.Enum):
    PASS = "PASS"                  # "No indicator detected by this check"
    REVIEW = "REVIEW"              # "Requires human review"
    UNAVAILABLE = "UNAVAILABLE"    # "Check unavailable / not applicable"


class AuthenticityCheck(TimestampMixin, Base):
    __tablename__ = "authenticity_checks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("applications.id"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False, index=True
    )
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)   # e.g. "file_integrity", "pdf_metadata", "pdf_structure", "image_indicators", "text_indicators", "signature_presence"
    check_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Human-readable title
    result: Mapped[AuthenticityResult] = mapped_column(SAEnum(AuthenticityResult), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=True)           # Supporting metadata / evidence dictionary
    screening_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    # Reviewer workflow (reusing FindingStatus conventions)
    reviewer_status: Mapped[FindingStatus] = mapped_column(
        SAEnum(FindingStatus), nullable=False, default=FindingStatus.OPEN
    )
    reviewer_notes: Mapped[str] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )

    application: Mapped["Application"] = relationship("Application", back_populates="authenticity_checks")
    document: Mapped["Document"] = relationship("Document", back_populates="authenticity_checks")
