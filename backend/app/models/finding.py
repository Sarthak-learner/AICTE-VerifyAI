"""Validation finding linking a rule violation to a source document and page."""
import enum
from sqlalchemy import String, Text, Integer, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"                 # Officer judged not applicable
    REQUIRES_CLARIFICATION = "requires_clarification"  # Reviewer requests clarification from applicant


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("applications.id"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id"), nullable=True  # None = cross-doc finding
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(SAEnum(FindingSeverity), nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        SAEnum(FindingStatus), nullable=False, default=FindingStatus.OPEN
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)   # 1-based; None if unknown
    extracted_value: Mapped[str] = mapped_column(Text, nullable=True)  # What was found
    expected_value: Mapped[str] = mapped_column(Text, nullable=True)   # What was expected
    evidence: Mapped[dict] = mapped_column(JSON, nullable=True)        # Arbitrary structured evidence
    # Advisory disclaimer is enforced at the API/UI layer, not stored per finding.
    resolved_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    resolution_note: Mapped[str] = mapped_column(Text, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="findings")
    document: Mapped["Document"] = relationship("Document", back_populates="findings")
