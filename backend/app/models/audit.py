"""Immutable audit event log."""
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    application_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("applications.id"), nullable=True, index=True
    )
    actor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    actor_label: Mapped[str] = mapped_column(String(255), nullable=True)  # Denormalised for log permanence
    action: Mapped[str] = mapped_column(String(128), nullable=False)       # e.g. "finding.resolved"
    resource_type: Mapped[str] = mapped_column(String(64), nullable=True)  # e.g. "finding"
    resource_id: Mapped[str] = mapped_column(String(64), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="audit_events")
