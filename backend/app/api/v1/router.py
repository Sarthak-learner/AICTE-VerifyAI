"""Central v1 API router — registers all endpoint sub-routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    applications,
    documents,
    processing,
    dashboard,
    validation,
    rules,
    authenticity,
    auth,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["Applications"],
)
# Document upload is nested under /applications/{id}/documents
api_router.include_router(
    documents.router,
    prefix="/applications",
    tags=["Documents"],
)
# OCR / extraction — also nested under /applications/{id}/documents/{id}/...
api_router.include_router(
    processing.router,
    prefix="/applications",
    tags=["Processing"],
)
# Validation rules & Cross-document consistency graph — nested under /applications/{id}/...
api_router.include_router(
    validation.router,
    prefix="/applications",
    tags=["Validation"],
)
# Authenticity screening — nested under /applications/{id}/...
api_router.include_router(
    authenticity.router,
    prefix="/applications",
    tags=["Authenticity"],
)
# Dashboard aggregation
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
# Configurable validation rules listing
api_router.include_router(
    rules.router,
    prefix="/rules",
    tags=["Rules"],
)
