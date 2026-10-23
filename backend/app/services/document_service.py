"""Document upload service: orchestrates ingestor + DB + duplicate detection."""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.audit import AuditEvent
from app.services.ingestor import IngestResult
from app.services.storage.interface import StorageBackend

logger = logging.getLogger(__name__)


def find_duplicate(db: Session, sha256_hash: str) -> Optional[Document]:
    """Return the first existing document with the same SHA-256 hash, or None."""
    return db.execute(
        select(Document).where(Document.sha256_hash == sha256_hash)
    ).scalar_one_or_none()


def create_document(
    db: Session,
    application_id: str,
    original_filename: str,
    document_type: Optional[str],
    result: IngestResult,
    storage: StorageBackend,
    actor_label: str = "system",
) -> tuple[Document, Optional[Document]]:
    """Persist document metadata.  Returns (document, duplicate_doc | None).

    If a duplicate is found the document is still stored (the file is already
    on disk from the ingestor).  We flag it and link it but do not reject it
    silently or auto-delete anything.

    Rollback safety: if the DB commit fails we delete the orphaned stored file.
    """
    # Duplicate detection
    existing = find_duplicate(db, result.sha256_hash)
    is_duplicate = existing is not None
    duplicate_of_id = existing.id if existing else None

    doc = Document(
        application_id=application_id,
        original_filename=original_filename,
        stored_filename=result.stored_filename,
        document_type=document_type,
        mime_type=result.mime_type,
        file_size_bytes=result.file_size_bytes,
        sha256_hash=result.sha256_hash,
        page_count=result.page_count,
        status=DocumentStatus.UPLOADED,
        is_duplicate=is_duplicate,
        duplicate_of_id=duplicate_of_id,
    )
    db.add(doc)
    db.flush()  # populate doc.id

    audit = AuditEvent(
        application_id=application_id,
        actor_label=actor_label,
        action="document.uploaded",
        resource_type="document",
        resource_id=doc.id,
        detail=(
            f"Uploaded '{original_filename}' ({result.mime_type}, "
            f"{result.file_size_bytes:,} bytes)"
            + (" [DUPLICATE]" if is_duplicate else "")
        ),
    )
    db.add(audit)

    try:
        db.commit()
    except Exception:
        # Rollback the orphaned stored file to avoid ghost files
        try:
            storage.delete(result.stored_filename)
        except Exception as del_err:
            logger.error("Could not delete orphaned file %s: %s",
                         result.stored_filename, del_err)
        raise

    db.refresh(doc)
    logger.info(
        "Document %s uploaded for application %s (duplicate=%s)",
        doc.id, application_id, is_duplicate,
    )
    return doc, existing


def list_documents(db: Session, application_id: str) -> tuple[int, list[Document]]:
    """Return total count and all documents for an application."""
    from sqlalchemy import func
    total = db.execute(
        select(func.count()).select_from(Document).where(
            Document.application_id == application_id
        )
    ).scalar_one()
    docs = (
        db.execute(
            select(Document)
            .where(Document.application_id == application_id)
            .order_by(Document.created_at.desc())
        )
        .scalars()
        .all()
    )
    return total, list(docs)


def get_document(
    db: Session, document_id: str, application_id: Optional[str] = None
) -> Optional[Document]:
    """Fetch a single document by ID with optional application scoping."""
    q = select(Document).where(Document.id == document_id)
    if application_id:
        q = q.where(Document.application_id == application_id)
    return db.execute(q).scalar_one_or_none()
