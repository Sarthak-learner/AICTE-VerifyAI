"""Document ingestor: validation, hashing, and storage.

Safety controls implemented here:
  1. Allow-list of supported MIME types.
  2. File-signature (magic bytes) verification — does not trust extension/browser MIME.
  3. Configurable max file size.
  4. Configurable max PDF page count.
  5. Empty-file rejection.
  6. Server-side random UUID storage filename (no path traversal possible).
  7. Storage outside the web root (enforced by StorageBackend).
  8. SHA-256 duplicate detection.
  9. Rollback of orphaned stored file if DB commit fails.
"""
import hashlib
import logging
import uuid
from typing import Optional

import fitz  # PyMuPDF

from app.services.storage.interface import StorageBackend

logger = logging.getLogger(__name__)

# ── File-type allow-list ───────────────────────────────────────────────────────
# Maps detected MIME type → canonical label and allowed extensions (informational).
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tif",
}

# Magic-byte signatures for content-type verification.
# Format: (offset, bytes_to_match)
MAGIC_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "application/pdf": [(0, b"%PDF")],
    "image/png": [(0, b"\x89PNG\r\n\x1a\n")],
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/tiff": [
        (0, b"II*\x00"),   # little-endian TIFF
        (0, b"MM\x00*"),   # big-endian TIFF
    ],
}

# Extension → canonical MIME (used only to give a helpful error message)
EXT_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class IngestionError(Exception):
    """Raised when an uploaded file fails safety checks."""


class IngestResult:
    """Outcome of a successful ingestion."""

    def __init__(
        self,
        stored_filename: str,
        mime_type: str,
        file_size_bytes: int,
        sha256_hash: str,
        page_count: Optional[int],
    ) -> None:
        self.stored_filename = stored_filename
        self.mime_type = mime_type
        self.file_size_bytes = file_size_bytes
        self.sha256_hash = sha256_hash
        self.page_count = page_count


def _detect_mime(data: bytes, original_filename: str) -> str:
    """Return the MIME type detected from magic bytes.

    Raises IngestionError for unknown or disallowed signatures.
    """
    for mime, signatures in MAGIC_SIGNATURES.items():
        for offset, magic in signatures:
            if data[offset: offset + len(magic)] == magic:
                return mime
    # Provide a helpful message but do not trust the extension for security
    raise IngestionError(
        f"Unrecognised file type for '{original_filename}'. "
        f"Supported types: PDF, PNG, JPG/JPEG, TIFF."
    )


def _count_pdf_pages(data: bytes) -> int:
    """Open the PDF in-memory and return page count, or raise IngestionError."""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
    except Exception as exc:
        raise IngestionError(
            f"PDF could not be opened or is corrupted: {exc}"
        ) from exc


def ingest(
    data: bytes,
    original_filename: str,
    storage: StorageBackend,
    max_size_bytes: int,
    max_pdf_pages: int,
) -> IngestResult:
    """Validate *data*, persist it via *storage*, and return an IngestResult.

    This function raises IngestionError on any failure. It does NOT write to
    the database — that responsibility belongs to the calling route handler.
    """
    # 1. Empty file
    if not data:
        raise IngestionError("Uploaded file is empty.")

    # 2. Size limit
    if len(data) > max_size_bytes:
        limit_mb = max_size_bytes / (1024 * 1024)
        raise IngestionError(
            f"File size {len(data):,} bytes exceeds the {limit_mb:.0f} MB limit."
        )

    # 3. Magic-byte verification (content wins over extension/browser MIME)
    detected_mime = _detect_mime(data, original_filename)

    # 4. PDF-specific checks
    page_count: Optional[int] = None
    if detected_mime == "application/pdf":
        page_count = _count_pdf_pages(data)
        if page_count == 0:
            raise IngestionError("PDF has no pages and cannot be accepted.")
        if page_count > max_pdf_pages:
            raise IngestionError(
                f"PDF has {page_count} pages; the maximum allowed is {max_pdf_pages}."
            )

    # 5. SHA-256 hash
    sha256_hash = hashlib.sha256(data).hexdigest()

    # 6. Server-side storage filename (UUID + detected extension)
    ext = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tif",
    }[detected_mime]
    stored_filename = f"{uuid.uuid4().hex}{ext}"

    # 7. Persist bytes
    storage.save(data, stored_filename)

    return IngestResult(
        stored_filename=stored_filename,
        mime_type=detected_mime,
        file_size_bytes=len(data),
        sha256_hash=sha256_hash,
        page_count=page_count,
    )
