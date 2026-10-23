"""Document processing (OCR + extraction) endpoints.

Routes:
  POST /api/v1/applications/{app_id}/documents/{doc_id}/process
      Triggers OCR and field extraction. Idempotent — re-running replaces results.

  GET  /api/v1/applications/{app_id}/documents/{doc_id}/extraction
      Returns the current extraction result (text + fields).
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_officer_or_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.document import DocumentStatus
from app.models.user import User
from app.schemas.extraction import (
    ExtractionResultSchema,
    ProcessingStatusResponse,
)
from app.services import application_service, document_service
from app.services.processing_service import ProcessingError, process_document
from app.services.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{application_id}/documents/{document_id}/process",
    response_model=ProcessingStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger OCR and field extraction for a document",
)
def trigger_processing(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
    current_user: User = Depends(require_officer_or_admin),
):
    """
    Trigger OCR text extraction and structured field extraction for a document.

    Restricted to OFFICER and ADMIN roles.
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

    storage = LocalStorageBackend(settings.upload_dir)

    try:
        doc = process_document(
            db=db,
            doc=doc,
            storage=storage,
            tesseract_cmd=settings.tesseract_cmd,
            actor_label=current_user.full_name or current_user.email,
        )
        return ProcessingStatusResponse(
            document_id=doc.id,
            status=doc.status,
            message=(
                "OCR and field extraction completed. "
                "Results are advisory — not verified against AICTE records."
            ),
        )
    except ProcessingError as exc:
        return ProcessingStatusResponse(
            document_id=document_id,
            status=DocumentStatus.FAILED,
            message=str(exc),
        )


@router.get(
    "/{application_id}/documents/{document_id}/extraction",
    response_model=ExtractionResultSchema,
    summary="Retrieve OCR and extraction results for a document",
)
def get_extraction(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve the current OCR text and extracted fields for a document.

    - `ocr_text_preview`: first 500 characters for display.
    - `extracted_fields`: structured JSON with advisory field values.
    - Fields are null if not found. No values are fabricated.
    - Storage paths are never returned.
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

    # Parse stored JSON fields
    extracted_fields_parsed: Optional[dict] = None
    warning: Optional[str] = None

    if doc.extracted_fields:
        try:
            extracted_fields_parsed = json.loads(doc.extracted_fields)
        except (json.JSONDecodeError, ValueError):
            warning = "Extracted fields data is malformed."

    # Check for extraction warning
    if doc.status == DocumentStatus.FAILED:
        if doc.mime_type in ("image/png", "image/jpeg", "image/tiff"):
            warning = (
                "Tesseract OCR binary was not available or failed during processing. "
                "Image text could not be extracted. "
                "Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        else:
            warning = "Document processing failed. No readable text could be extracted."
    elif doc.status == DocumentStatus.PROCESSED and not doc.ocr_text:
        warning = "No readable text was detected in this document."

    ocr_preview = (doc.ocr_text or "")[:500] if doc.ocr_text else None

    return ExtractionResultSchema(
        document_id=doc.id,
        status=doc.status,
        ocr_text=doc.ocr_text,
        ocr_text_preview=ocr_preview,
        extracted_fields=extracted_fields_parsed,
        page_count=doc.page_count,
        warning=warning,
    )
