"""Health-check endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter()

DISCLAIMER = (
    "AI-generated findings are advisory only. "
    "They do not constitute proof of document forgery "
    "or a final AICTE regulatory decision."
)


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health_check(
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> HealthResponse:
    """
    Returns the operational status of the API and its database connection.
    This endpoint does not require authentication.
    """
    db_status = "unreachable"
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
        database=db_status,
        disclaimer=DISCLAIMER,
    )
