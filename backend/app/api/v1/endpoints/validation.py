"""Validation and Cross-Document Consistency endpoints.

Routes:
  POST  /api/v1/applications/{app_id}/validate
        Runs validation and cross-document consistency checks; persists findings idempotently.

  GET   /api/v1/applications/{app_id}/findings
        Lists all findings for an application with status/severity filtering.

  GET   /api/v1/applications/{app_id}/consistency-graph
        Retrieves the structured cross-document consistency graph and side-by-side comparisons.

  PATCH /api/v1/applications/{app_id}/findings/{finding_id}
        Allows an authorized reviewer to update review status and append resolution notes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user, require_officer_or_admin
from app.db.session import get_db
from app.models.application import Application
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.finding import (
    ConsistencyGraphResponse,
    FindingListResponse,
    FindingResponse,
    FindingUpdatePayload,
    ValidationRunResponse,
)
from app.services.validation.engine import build_consistency_graph, run_application_validation
from app.models.document import Document

router = APIRouter()


@router.post(
    "/{application_id}/validate",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run validation rules and cross-document consistency checks",
)
def validate_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Execute rule engine and cross-document consistency comparisons on an application.

    - Single-document checks (presence, expiry dates, demo baseline parameters).
    - Cross-document field consistency (normalized institution names, land area, programmes).
    - Generates and returns the consistency graph and side-by-side comparisons.
    - Idempotent: re-running updates findings without creating duplicates.
    - Preserves any prior resolutions made by a human reviewer.
    """
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    try:
        findings, graph_data = run_application_validation(
            db, application_id, actor_label=current_user.full_name or current_user.email
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation run failed: {str(exc)}",
        ) from exc

    return ValidationRunResponse(
        application_id=application_id,
        total_findings=len(findings),
        findings=[FindingResponse.model_validate(f) for f in findings],
        consistency_graph=ConsistencyGraphResponse(**graph_data),
        message=f"Validation completed. {len(findings)} findings recorded. {graph_data['total_discrepancies']} cross-document discrepancies flagged.",
    )


@router.get(
    "/{application_id}/findings",
    response_model=FindingListResponse,
    summary="List validation findings for an application",
)
def list_findings(
    application_id: str,
    status_filter: Optional[FindingStatus] = Query(None, alias="status"),
    severity_filter: Optional[FindingSeverity] = Query(None, alias="severity"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve validation findings for an application with optional status or severity filters."""
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    q = select(Finding).where(Finding.application_id == application_id)
    if status_filter:
        q = q.where(Finding.status == status_filter)
    if severity_filter:
        q = q.where(Finding.severity == severity_filter)

    q = q.order_by(Finding.created_at.desc())
    findings = db.execute(q).scalars().all()

    # Aggregate counts across all findings for this application
    all_findings = db.execute(
        select(Finding).where(Finding.application_id == application_id)
    ).scalars().all()

    open_c = sum(1 for f in all_findings if f.status == FindingStatus.OPEN)
    resolved_c = sum(1 for f in all_findings if f.status == FindingStatus.RESOLVED)
    under_review_c = sum(1 for f in all_findings if f.status == FindingStatus.UNDER_REVIEW)
    clarification_c = sum(1 for f in all_findings if f.status == FindingStatus.REQUIRES_CLARIFICATION)

    return FindingListResponse(
        total=len(findings),
        open_count=open_c,
        resolved_count=resolved_c,
        under_review_count=under_review_c,
        requires_clarification_count=clarification_c,
        items=[FindingResponse.model_validate(f) for f in findings],
    )


@router.get(
    "/{application_id}/consistency-graph",
    response_model=ConsistencyGraphResponse,
    summary="Get cross-document consistency graph and side-by-side comparisons",
)
def get_consistency_graph(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the structured cross-document consistency graph and comparison items."""
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

    _, graph_data = build_consistency_graph(app, list(docs))
    return ConsistencyGraphResponse(**graph_data)


@router.patch(
    "/{application_id}/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Update finding review status and resolution notes",
)
def update_finding_status(
    application_id: str,
    finding_id: str,
    payload: FindingUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Allow an authorized reviewer to update the status of a finding and record notes.

    Restricted to OFFICER and ADMIN roles.
    """
    finding = db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.application_id == application_id,
        )
    ).scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found for application '{application_id}'.",
        )

    old_status = finding.status
    finding.status = payload.status
    if payload.resolution_note is not None:
        finding.resolution_note = payload.resolution_note

    # Record Reviewer Action in Audit Log
    reviewer_name = payload.reviewer_label or current_user.full_name or current_user.email
    audit = AuditEvent(
        application_id=application_id,
        actor_label=reviewer_name,
        action="finding.reviewed",
        resource_type="finding",
        resource_id=finding.id,
        detail=(
            f"Finding '{finding.rule_code}' status updated from '{old_status.value}' to '{payload.status.value}'. "
            + (f"Note: {payload.resolution_note}" if payload.resolution_note else "")
        ),
        metadata_={
            "old_status": old_status.value,
            "new_status": payload.status.value,
            "resolution_note": payload.resolution_note,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(finding)

    return FindingResponse.model_validate(finding)
