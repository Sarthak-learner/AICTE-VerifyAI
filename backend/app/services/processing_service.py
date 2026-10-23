"""Processing service: orchestrates OCR + field extraction + DB updates.

Responsibilities:
  - Read the stored file from private storage (never exposed publicly).
  - Run OCR via ocr.engine.run_extraction.
  - Run structured field extraction via extraction.fields.extract_fields.
  - Update the Document record (ocr_text, extracted_fields, status).
  - Record audit events.
  - Ensure idempotency: re-processing replaces previous results, does NOT create duplicates.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.audit import AuditEvent
from app.services.ocr.engine import run_extraction, ExtractionResult
from app.services.extraction.fields import extract_fields, ExtractedFields
from app.services.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Raised when document processing fails for a user-visible reason."""


def _load_file(storage: LocalStorageBackend, stored_filename: str) -> bytes:
    """Read stored file bytes without exposing internal paths."""
    from pathlib import Path
    root = storage._root
    path = root / stored_filename
    if not path.exists():
        raise ProcessingError("Stored file not found. The document may have been moved or deleted.")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ProcessingError(f"Cannot read stored file: {type(exc).__name__}") from exc


def process_document(
    db: Session,
    doc: Document,
    storage: LocalStorageBackend,
    tesseract_cmd: str = "tesseract",
    actor_label: str = "system",
) -> Document:
    """Run OCR + extraction on *doc* and persist results.

    Idempotent: calling multiple times replaces previous extraction data
    without creating new Document rows.

    Returns the updated Document instance.
    Raises ProcessingError on failure (status → FAILED is set in the DB).
    """
    # Mark as PROCESSING
    doc.status = DocumentStatus.PROCESSING
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # 1. Load file bytes privately
        data = _load_file(storage, doc.stored_filename)

        # 2. Run OCR
        extraction: ExtractionResult = run_extraction(
            data=data,
            mime_type=doc.mime_type,
            tesseract_cmd=tesseract_cmd,
        )

        # 3. Check for successful text extraction
        full_text = (extraction.full_text or "").strip()
        extraction_error = extraction.error

        if not full_text:
            err_msg = extraction_error or "No readable text could be extracted from this document."
            raise ProcessingError(err_msg)

        # 4. Run field extraction from page texts
        page_texts = [(p.page_number, p.text) for p in extraction.pages if p.text]
        extracted: ExtractedFields = extract_fields(page_texts)

        # 5. Persist results (replace any previous extraction - retry safe)
        doc.ocr_text = full_text
        doc.extracted_fields = extracted.to_json()
        doc.status = DocumentStatus.PROCESSED

        db.add(doc)

        # Record audit event
        audit = AuditEvent(
            application_id=doc.application_id,
            actor_label=actor_label,
            action="document.processed",
            resource_type="document",
            resource_id=doc.id,
            detail=(
                f"OCR completed for '{doc.original_filename}'. "
                f"Pages: {len(extraction.pages)}, "
                f"Text length: {len(full_text)} chars"
                + (f". Warning: {extraction_error}" if extraction_error else "")
            ),
        )
        db.add(audit)
        db.commit()
        db.refresh(doc)

        logger.info("Processed document %s — %d pages, %d chars",
                    doc.id, len(extraction.pages), len(full_text))
        return doc

    except ProcessingError as exc:
        _mark_failed(db, doc, actor_label, detail=str(exc))
        raise
    except Exception as exc:
        logger.exception("Unexpected error processing document %s", doc.id)
        _mark_failed(db, doc, actor_label, detail=str(type(exc).__name__))
        raise ProcessingError(f"Extraction failed: {type(exc).__name__}") from exc


def _mark_failed(
    db: Session, doc: Document, actor_label: str, detail: str = ""
) -> None:
    """Set document status to FAILED and record audit event."""
    try:
        doc.status = DocumentStatus.FAILED
        doc.ocr_text = None
        doc.extracted_fields = ExtractedFields().to_json()
        db.add(doc)
        audit = AuditEvent(
            application_id=doc.application_id,
            actor_label=actor_label,
            action="document.processing_failed",
            resource_type="document",
            resource_id=doc.id,
            detail=f"Processing failed for '{doc.original_filename}'" + (f": {detail}" if detail else ""),
        )
        db.add(audit)
        db.commit()
    except Exception:
        logger.exception("Could not mark document %s as FAILED", doc.id)
