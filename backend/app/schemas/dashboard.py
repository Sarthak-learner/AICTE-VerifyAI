"""Pydantic schemas for dashboard aggregation data."""
from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class DashboardStats(BaseModel):
    """Aggregated statistics for the dashboard charts.

    All counts reflect persisted database records.
    These are raw counts — no fabricated or demo data.
    """
    # Summary cards
    total_applications: int
    total_documents: int
    processed_documents: int   # DocumentStatus.PROCESSED count

    # Chart data
    applications_by_status: list[StatusCount]     # for bar/pie
    documents_by_status: list[StatusCount]         # for bar chart
    documents_by_category: list[CategoryCount]     # for bar chart
