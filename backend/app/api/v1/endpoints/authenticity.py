"""Authenticity Screening Endpoints for AICTE VerifyAI.

Routes:
  POST  /api/v1/applications/{application_id}/authenticity-screen
        Executes file integrity, metadata, structural, image, text, and signature screening.

  GET   /api/v1/applications/{application_id}/authenticity-checks
        Retrieves authenticity checks grouped by document with metrics.

  PATCH /api/v1/applications/{application_id}/authenticity-checks/{check_id}
        Updates reviewer status and resolution notes, emitting an audit log entry.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_officer_or_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.application import Application
from app.models.document import Document
from app.models.authenticity import AuthenticityCheck, AuthenticityResult
from app.models.finding import FindingStatus
from app.models.user import User
from app.schemas.authenticity import (
    AuthenticityCheckResponse,
    AuthenticityCheckUpdatePayload,
    AuthenticityScreeningResponse,
    DocumentAuthenticityGroup,
)
from app.services.authenticity.screening import (
    run_application_screening,
    update_check_review_status,
)
from app.services.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_storage(settings=Depends(get_settings)) -> LocalStorageBackend:
    return LocalStorageBackend(settings.upload_dir)


def _build_screening_response(
    application_id: str,
    checks: List[AuthenticityCheck],
    docs: List[Document],
    message: str = "Authenticity screening completed.",
) -> AuthenticityScreeningResponse:
    """Format check list into grouped document responses and analytics."""
    doc_map = {d.id: d for d in docs}
    doc_checks_map: dict[str, list[AuthenticityCheckResponse]] = {}

    for d in docs:
        doc_checks_map[d.id] = []

    check_responses: List[AuthenticityCheckResponse] = []
    total_passed = 0
    total_review = 0
    total_unavailable = 0

    for c in checks:
        d = doc_map.get(c.document_id)
        resp = AuthenticityCheckResponse(
            id=c.id,
            application_id=c.application_id,
            document_id=c.document_id,
            document_filename=d.original_filename if d else None,
            document_type=d.document_type if d else None,
            check_type=c.check_type,
            check_name=c.check_name,
            result=c.result,
            explanation=c.explanation,
            evidence=c.evidence,
            screening_version=c.screening_version,
            reviewer_status=c.reviewer_status,
            reviewer_notes=c.reviewer_notes,
            resolved_by_id=c.resolved_by_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        check_responses.append(resp)
        if c.document_id in doc_checks_map:
            doc_checks_map[c.document_id].append(resp)

        if c.result == AuthenticityResult.PASS:
            total_passed += 1
        elif c.result == AuthenticityResult.REVIEW:
            total_review += 1
        else:
            total_unavailable += 1

    grouped: List[DocumentAuthenticityGroup] = []
    for d in docs:
        doc_checks = doc_checks_map.get(d.id, [])
        grouped.append(
            DocumentAuthenticityGroup(
                document_id=d.id,
                document_filename=d.original_filename,
                document_type=d.document_type,
                checks=doc_checks,
                pass_count=sum(1 for x in doc_checks if x.result == AuthenticityResult.PASS),
                review_count=sum(1 for x in doc_checks if x.result == AuthenticityResult.REVIEW),
                unavailable_count=sum(1 for x in doc_checks if x.result == AuthenticityResult.UNAVAILABLE),
            )
        )

    return AuthenticityScreeningResponse(
        application_id=application_id,
        total_checks=len(checks),
        total_passed=total_passed,
        total_review_required=total_review,
        total_unavailable=total_unavailable,
        documents=grouped,
        checks=check_responses,
        message=message,
    )


@router.post(
    "/{application_id}/authenticity-screen",
    response_model=AuthenticityScreeningResponse,
    status_code=status.HTTP_200_OK,
    summary="Run deterministic authenticity screening checks on application documents",
)
def screen_application_documents(
    application_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorageBackend = Depends(_get_storage),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Execute authenticity screening across all documents for the application.

    Restricted to OFFICER and ADMIN roles.
    """
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    docs = db.execute(
        select(Document).where(Document.application_id == application_id)
    ).scalars().all()

    try:
        checks = run_application_screening(
            db, application_id, storage, actor_label=current_user.full_name or current_user.email
        )
    except Exception as exc:
        logger.exception("Authenticity screening failed for application %s", application_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authenticity screening error: {str(exc)}",
        ) from exc

    review_count = sum(1 for c in checks if c.result == AuthenticityResult.REVIEW)
    msg = f"Authenticity screening completed for {len(docs)} document(s). {review_count} item(s) require review."

    return _build_screening_response(application_id, checks, list(docs), msg)


@router.get(
    "/{application_id}/authenticity-checks",
    response_model=AuthenticityScreeningResponse,
    summary="Get authenticity screening checks and metrics for an application",
)
def get_authenticity_checks(
    application_id: str,
    document_id: Optional[str] = Query(None, description="Filter by specific document ID"),
    result_filter: Optional[AuthenticityResult] = Query(None, alias="result"),
    reviewer_status: Optional[FindingStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve existing authenticity screening checks grouped by document with metrics."""
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    q = select(AuthenticityCheck).where(AuthenticityCheck.application_id == application_id)
    if document_id:
        q = q.where(AuthenticityCheck.document_id == document_id)
    if result_filter:
        q = q.where(AuthenticityCheck.result == result_filter)
    if reviewer_status:
        q = q.where(AuthenticityCheck.reviewer_status == reviewer_status)

    q = q.order_by(AuthenticityCheck.created_at.asc())
    checks = db.execute(q).scalars().all()

    docs = db.execute(
        select(Document).where(Document.application_id == application_id)
    ).scalars().all()

    return _build_screening_response(
        application_id,
        list(checks),
        list(docs),
        "Retrieved authenticity screening results.",
    )


@router.patch(
    "/{application_id}/authenticity-checks/{check_id}",
    response_model=AuthenticityCheckResponse,
    summary="Update reviewer status and resolution notes for an authenticity check",
)
def update_authenticity_check_review(
    application_id: str,
    check_id: str,
    payload: AuthenticityCheckUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Allow an authorized reviewer to set check status and append resolution notes.

    Restricted to OFFICER and ADMIN roles.
    """
    reviewer_name = payload.reviewer_label or current_user.full_name or current_user.email
    try:
        check = update_check_review_status(
            db=db,
            application_id=application_id,
            check_id=check_id,
            new_status=payload.reviewer_status,
            notes=payload.reviewer_notes,
            actor_label=reviewer_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    doc = db.execute(
        select(Document).where(Document.id == check.document_id)
    ).scalar_one_or_none()

    return AuthenticityCheckResponse(
        id=check.id,
        application_id=check.application_id,
        document_id=check.document_id,
        document_filename=doc.original_filename if doc else None,
        document_type=doc.document_type if doc else None,
        check_type=check.check_type,
        check_name=check.check_name,
        result=check.result,
        explanation=check.explanation,
        evidence=check.evidence,
        screening_version=check.screening_version,
        reviewer_status=check.reviewer_status,
        reviewer_notes=check.reviewer_notes,
        resolved_by_id=check.resolved_by_id,
        created_at=check.created_at,
        updated_at=check.updated_at,
    )
