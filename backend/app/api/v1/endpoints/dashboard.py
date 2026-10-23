"""Dashboard aggregation endpoint.

Provides real counts from the database for frontend charts.
No fake/demo data — all values reflect persisted records.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.application import Application, ApplicationStatus
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.dashboard import CategoryCount, DashboardStats, StatusCount

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Dashboard aggregation statistics",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns live aggregated counts from the database for visualisations.

    All numbers reflect actual persisted records — no demo data.
    """
    # --- Summary counts ---
    total_applications = db.execute(
        select(func.count()).select_from(Application)
    ).scalar_one()

    total_documents = db.execute(
        select(func.count()).select_from(Document)
    ).scalar_one()

    processed_documents = db.execute(
        select(func.count()).select_from(Document).where(
            Document.status == DocumentStatus.PROCESSED
        )
    ).scalar_one()

    # --- Applications by status ---
    app_status_rows = db.execute(
        select(Application.status, func.count(Application.id).label("cnt"))
        .group_by(Application.status)
    ).all()

    # Include all statuses, defaulting absent ones to 0
    app_status_map = {row.status: row.cnt for row in app_status_rows}
    applications_by_status = [
        StatusCount(status=s.value, count=app_status_map.get(s, 0))
        for s in ApplicationStatus
    ]

    # --- Documents by status ---
    doc_status_rows = db.execute(
        select(Document.status, func.count(Document.id).label("cnt"))
        .group_by(Document.status)
    ).all()
    doc_status_map = {row.status: row.cnt for row in doc_status_rows}
    documents_by_status = [
        StatusCount(status=s.value, count=doc_status_map.get(s, 0))
        for s in DocumentStatus
    ]

    # --- Documents by category ---
    doc_category_rows = db.execute(
        select(
            func.coalesce(Document.document_type, "uncategorised").label("category"),
            func.count(Document.id).label("cnt"),
        )
        .group_by("category")
    ).all()
    documents_by_category = [
        CategoryCount(category=row.category, count=row.cnt)
        for row in doc_category_rows
    ]

    return DashboardStats(
        total_applications=total_applications,
        total_documents=total_documents,
        processed_documents=processed_documents,
        applications_by_status=applications_by_status,
        documents_by_status=documents_by_status,
        documents_by_category=documents_by_category,
    )
