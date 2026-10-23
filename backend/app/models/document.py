"""Uploaded document record."""
import enum
from sqlalchemy import String, Integer, Text, Enum as SAEnum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("applications.id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)  # UUID-based safe name
    document_type: Mapped[str] = mapped_column(String(128), nullable=True)    # e.g. "land_deed", "noc"
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), nullable=False, default=DocumentStatus.UPLOADED
    )
    ocr_text: Mapped[str] = mapped_column(Text, nullable=True)              # Full extracted text
    extracted_fields: Mapped[str] = mapped_column(Text, nullable=True)      # JSON blob of key-value pairs
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id"), nullable=True
    )

    application: Mapped["Application"] = relationship("Application", back_populates="documents")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="document")
    authenticity_checks: Mapped[list["AuthenticityCheck"]] = relationship("AuthenticityCheck", back_populates="document")
