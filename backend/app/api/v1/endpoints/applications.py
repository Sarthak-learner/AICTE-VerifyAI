"""Application CRUD endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_officer_or_admin
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationList,
    ApplicationListItem,
    ApplicationResponse,
    AuditEventResponse,
    AuditTrailResponse,
)

from app.schemas.document import DocumentList, DocumentListItem
from app.services import application_service, document_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Create a new institutional approval application in DRAFT status.

    Restricted to OFFICER and ADMIN roles.
    """
    try:
        app = application_service.create_application(
            db, payload, actor_label=current_user.full_name or current_user.email
        )
    except Exception as exc:
        logger.exception("Failed to create application")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save application. Please try again.",
        ) from exc
    return app


@router.get(
    "",
    response_model=ApplicationList,
    summary="List all applications",
)
def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return a paginated list of applications ordered newest first."""
    total, apps = application_service.list_applications(db, skip=skip, limit=limit)
    return ApplicationList(
        total=total,
        items=[ApplicationListItem.model_validate(a) for a in apps],
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get application by ID",
)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fetch a single application's full details."""
    app = application_service.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )
    return app


@router.get(
    "/{application_id}/documents",
    response_model=DocumentList,
    summary="List documents for an application",
)
def list_application_documents(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return metadata for all documents uploaded to this application.

    Storage paths are never included in the response.
    """
    app = application_service.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )
    total, docs = document_service.list_documents(db, application_id)
    return DocumentList(
        total=total,
        items=[DocumentListItem.model_validate(d) for d in docs],
    )


@router.get(
    "/{application_id}/audit-trail",
    response_model=AuditTrailResponse,
    summary="Get immutable regulatory audit trail for an application",
)
def get_application_audit_trail(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve chronological audit events for an application.

    Tracks application creation, document uploads, automated validation runs,
    authenticity screening runs, and human reviewer decisions.
    """
    app = application_service.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )
    events = (
        db.execute(
            select(AuditEvent)
            .where(AuditEvent.application_id == application_id)
            .order_by(AuditEvent.created_at.desc())
        )
        .scalars()
        .all()
    )
    return AuditTrailResponse(
        application_id=application_id,
        total=len(events),
        events=[AuditEventResponse.model_validate(e) for e in events],
    )

