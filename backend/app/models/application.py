"""Institutional approval application."""
import enum
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VALIDATION_COMPLETE = "validation_complete"
    APPROVED = "approved"      # Placeholder only — no AI system grants final approval
    REJECTED = "rejected"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    reference_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    institution_name: Mapped[str] = mapped_column(String(512), nullable=False)
    aicte_permanent_id: Mapped[str] = mapped_column(String(64), nullable=True)  # AICTE PID or demo identifier
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)       # e.g. "2025-26"
    application_category: Mapped[str] = mapped_column(String(64), nullable=False)
    programme_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    institution_type: Mapped[str] = mapped_column(String(128), nullable=True)
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    applicant_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus), nullable=False, default=ApplicationStatus.DRAFT
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_officer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="application")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="application")
    authenticity_checks: Mapped[list["AuthenticityCheck"]] = relationship("AuthenticityCheck", back_populates="application")
    audit_events: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="application")
