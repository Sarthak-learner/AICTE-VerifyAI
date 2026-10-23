"""Configurable validation rule."""
import enum
from sqlalchemy import String, Text, Boolean, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.base_mixin import TimestampMixin, new_uuid


class RuleSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationRule(TimestampMixin, Base):
    __tablename__ = "validation_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)   # e.g. "EXPIRY_CHECK"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    applies_to_document_type: Mapped[str] = mapped_column(String(128), nullable=True)  # None = all
    severity: Mapped[RuleSeverity] = mapped_column(
        SAEnum(RuleSeverity), nullable=False, default=RuleSeverity.WARNING
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=True)  # Rule-specific config
    # NOTE: All thresholds here are DEMO values. Replace with verified AICTE requirements.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
