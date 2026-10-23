"""Document upload and retrieval endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_officer_or_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DOCUMENT_CATEGORIES,
    DocumentResponse,
    DuplicateInfo,
    UploadResponse,
)
from app.services import application_service, document_service
from app.services.ingestor import IngestionError, ingest
from app.services.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_storage(settings=Depends(get_settings)):
    return LocalStorageBackend(settings.upload_dir)


@router.post(
    "/{application_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to an application",
)
async def upload_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Upload a supporting document (PDF, PNG, JPG/JPEG, TIFF) to an application.

    Safety controls:
    - File-signature (magic byte) verification — extension and browser MIME are not trusted.
    - Configurable size and PDF page-count limits.
    - SHA-256 duplicate detection.
    - Server-side UUID storage filename.

    **Advisory:** A successful upload only confirms the file passed ingestion checks.
    It does not authenticate the document or validate it against AICTE requirements.

    **Access control note (Prototype):** Unauthenticated. Auth will be added later.
    """
    # Validate application exists
    app = application_service.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    # Validate document_type if supplied
    if document_type and document_type not in DOCUMENT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"document_type must be one of: {DOCUMENT_CATEGORIES}",
        )

    # Read file bytes
    data = await file.read()

    # Ingest (validate + store)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    max_pages = getattr(settings, "max_pdf_pages", 500)
    storage = LocalStorageBackend(settings.upload_dir)

    try:
        result = ingest(
            data=data,
            original_filename=file.filename or "upload",
            storage=storage,
            max_size_bytes=max_bytes,
            max_pdf_pages=max_pages,
        )
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Persist metadata
    try:
        doc, duplicate = document_service.create_document(
            db=db,
            application_id=application_id,
            original_filename=file.filename or "upload",
            document_type=document_type,
            result=result,
            storage=storage,
            actor_label=current_user.full_name or current_user.email,
        )
    except Exception as exc:
        logger.exception("Database error after file stored")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File was stored but metadata could not be saved. Please contact support.",
        ) from exc

    dup_info: Optional[DuplicateInfo] = None
    if duplicate:
        dup_info = DuplicateInfo(
            existing_document_id=duplicate.id,
            existing_application_id=duplicate.application_id,
            message=(
                "This file's content is identical to an existing document. "
                "An exact hash match indicates identical file contents but does not "
                "by itself confirm or deny document authenticity."
            ),
        )

    return UploadResponse(document=DocumentResponse.model_validate(doc), duplicate=dup_info)


@router.get(
    "/{application_id}/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
)
def get_document(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return metadata for a specific document.

    Storage paths and file content are never returned.
    """
    app = application_service.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )
    doc = document_service.get_document(db, document_id, application_id=application_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc
