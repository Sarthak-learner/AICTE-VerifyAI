"""Application CRUD service."""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.audit import AuditEvent
from app.schemas.application import ApplicationCreate

logger = logging.getLogger(__name__)

_REF_PREFIX = "APP"


def _generate_reference_number() -> str:
    """Generate a short unique application reference like APP-2025-A3F7."""
    year = datetime.now(timezone.utc).year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{_REF_PREFIX}-{year}-{suffix}"


def create_application(
    db: Session,
    payload: ApplicationCreate,
    actor_label: str = "system",
) -> Application:
    """Persist a new Application in DRAFT status and record an audit event."""
    app = Application(
        reference_number=_generate_reference_number(),
        institution_name=payload.institution_name,
        aicte_permanent_id=payload.aicte_permanent_id,
        academic_year=payload.academic_year,
        application_category=payload.application_category,
        programme_type=payload.programme_type,
        description=payload.description,
        applicant_name=payload.applicant_name,
        applicant_email=payload.applicant_email,
        status=ApplicationStatus.DRAFT,
    )
    db.add(app)
    db.flush()  # populate app.id before audit row

    audit = AuditEvent(
        application_id=app.id,
        actor_label=actor_label,
        action="application.created",
        resource_type="application",
        resource_id=app.id,
        detail=f"Application created for {payload.institution_name} ({payload.academic_year})",
    )
    db.add(audit)
    db.commit()
    db.refresh(app)
    logger.info("Created application %s (ref: %s)", app.id, app.reference_number)
    return app


def list_applications(
    db: Session,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[Application]]:
    """Return total count and paginated list of applications."""
    from sqlalchemy import func, select

    total = db.execute(select(func.count()).select_from(Application)).scalar_one()
    apps = (
        db.execute(
            select(Application)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return total, list(apps)


def get_application(db: Session, application_id: str) -> Optional[Application]:
    """Fetch a single application by ID; returns None if not found."""
    from sqlalchemy import select
    return db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()
