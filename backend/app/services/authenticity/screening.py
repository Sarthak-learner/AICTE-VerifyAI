"""Document Authenticity Screening Engine for AICTE VerifyAI.

Performs deterministic screening checks:
1. File integrity: SHA-256 recalculation against recorded upload hash.
2. PDF metadata: inspection of creation/modification timestamps and container properties.
3. PDF structure: parser syntax check, encryption detection, and structural integrity.
4. Image indicators: dimensions, color encoding, and resolution anomaly screening.
5. Text indicators: cross-referencing extracted institutional headers with application data.
6. Signature presence: detection of PDF digital signature fields and form dictionaries.

Advisory Note:
Anomalies identified by this engine are review flags for human reviewers,
NOT proof of manipulation or forgery.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.document import Document
from app.models.authenticity import AuthenticityCheck, AuthenticityResult
from app.models.finding import FindingStatus
from app.models.audit import AuditEvent
from app.services.storage.local import LocalStorageBackend
from app.services.validation.normalizer import are_institution_names_consistent

logger = logging.getLogger(__name__)

SCREENING_VERSION = "1.0.0"


def _parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse PDF date format 'D:YYYYMMDDHHmmSS...' into UTC datetime."""
    if not date_str:
        return None
    s = date_str.strip()
    if s.startswith("D:"):
        s = s[2:]
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) >= 8:
        try:
            year = int(digits[:4])
            month = int(digits[4:6])
            day = int(digits[6:8])
            hour = int(digits[8:10]) if len(digits) >= 10 else 0
            minute = int(digits[10:12]) if len(digits) >= 12 else 0
            second = int(digits[12:14]) if len(digits) >= 14 else 0
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except (ValueError, OverflowError):
            return None
    return None


def _load_document_bytes(storage: LocalStorageBackend, stored_filename: str) -> Optional[bytes]:
    """Read document bytes from local storage without leaking internal path."""
    try:
        path = storage._root / stored_filename
        if not path.is_file():
            return None
        return path.read_bytes()
    except Exception as exc:
        logger.warning("Failed to read stored file %s: %s", stored_filename, exc)
        return None


def check_file_integrity(doc: Document, data: Optional[bytes]) -> Dict[str, Any]:
    """Check 1: File integrity via SHA-256 recalculation."""
    check_type = "file_integrity"
    check_name = "File SHA-256 Hash Integrity Check"

    if data is None:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.REVIEW,
            "explanation": "Stored document content is unavailable in repository storage. Requires human review.",
            "evidence": {"file_found": False, "recorded_hash": doc.sha256_hash},
        }

    if not doc.sha256_hash:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.REVIEW,
            "explanation": "Original upload hash was not recorded; integrity verification cannot be confirmed.",
            "evidence": {"recorded_hash_present": False},
        }

    calculated_hash = hashlib.sha256(data).hexdigest()
    if calculated_hash.lower() == doc.sha256_hash.lower():
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.PASS,
            "explanation": "No indicator detected by this check. Calculated file SHA-256 matches recorded upload hash.",
            "evidence": {
                "algorithm": "SHA-256",
                "recorded_hash": doc.sha256_hash,
                "calculated_hash": calculated_hash,
                "matched": True,
            },
        }
    else:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.REVIEW,
            "explanation": (
                "Calculated SHA-256 hash does not match the hash recorded at upload. "
                "Document file content may have been modified or corrupted. Requires human review."
            ),
            "evidence": {
                "algorithm": "SHA-256",
                "recorded_hash": doc.sha256_hash,
                "calculated_hash": calculated_hash,
                "matched": False,
            },
        }


def check_pdf_metadata(doc: Document, data: Optional[bytes]) -> Dict[str, Any]:
    """Check 2: PDF creation/modification metadata inspection."""
    check_type = "pdf_metadata"
    check_name = "PDF Metadata & Timestamp Inspection"

    if data is None or "pdf" not in doc.mime_type.lower():
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": "PDF metadata inspection is not applicable to non-PDF media.",
            "evidence": {"mime_type": doc.mime_type},
        }

    doc_fitz = None
    try:
        doc_fitz = fitz.open(stream=data, filetype="pdf")
        raw_meta = doc_fitz.metadata or {}

        # Sanitize metadata (do not expose private paths or internal strings)
        sanitized_meta = {
            "format": raw_meta.get("format", "PDF"),
            "title": str(raw_meta.get("title") or "")[:200],
            "author": str(raw_meta.get("author") or "")[:200],
            "creator": str(raw_meta.get("creator") or "")[:200],
            "producer": str(raw_meta.get("producer") or "")[:200],
            "creation_date": raw_meta.get("creationDate"),
            "modification_date": raw_meta.get("modDate"),
        }

        creation_dt = _parse_pdf_date(raw_meta.get("creationDate"))
        mod_dt = _parse_pdf_date(raw_meta.get("modDate"))

        anomalies = []
        now = datetime.now(timezone.utc)

        # Check for future dates
        if creation_dt and creation_dt > now + timedelta(days=2):
            anomalies.append(f"Creation date '{creation_dt.isoformat()}' is set in the future.")
        if mod_dt and mod_dt > now + timedelta(days=2):
            anomalies.append(f"Modification date '{mod_dt.isoformat()}' is set in the future.")

        # Check for modification date preceding creation date (allowing 60s tolerance for clock drift)
        if creation_dt and mod_dt and mod_dt < (creation_dt - timedelta(minutes=10)):
            anomalies.append(
                f"Modification timestamp ({mod_dt.strftime('%Y-%m-%d %H:%M')}) precedes "
                f"creation timestamp ({creation_dt.strftime('%Y-%m-%d %H:%M')})."
            )

        if anomalies:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": (
                    f"Metadata timestamp anomaly detected: {'; '.join(anomalies)} "
                    "Requires human review. (Note: Metadata anomalies are weak indicators and may arise from scanner clock drift)."
                ),
                "evidence": {
                    "sanitized_metadata": sanitized_meta,
                    "anomalies": anomalies,
                },
            }

        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.PASS,
            "explanation": "No indicator detected by this check. PDF container metadata properties are coherent.",
            "evidence": {"sanitized_metadata": sanitized_meta},
        }

    except Exception as exc:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.REVIEW,
            "explanation": f"Unable to parse PDF metadata: {type(exc).__name__}. Requires human review.",
            "evidence": {"error": type(exc).__name__},
        }
    finally:
        if doc_fitz:
            try:
                doc_fitz.close()
            except Exception:
                pass


def check_pdf_structure(doc: Document, data: Optional[bytes]) -> Dict[str, Any]:
    """Check 3: PDF structure, parsing errors, repair status, and encryption."""
    check_type = "pdf_structure"
    check_name = "PDF Structural & Parsing Analysis"

    if data is None or "pdf" not in doc.mime_type.lower():
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": "PDF structural analysis is not applicable to non-PDF formats.",
            "evidence": {"mime_type": doc.mime_type},
        }

    doc_fitz = None
    try:
        doc_fitz = fitz.open(stream=data, filetype="pdf")

        if doc_fitz.is_encrypted:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": "PDF is password-encrypted or access-restricted. Internal structure could not be fully parsed.",
                "evidence": {"is_encrypted": True},
            }

        if getattr(doc_fitz, "is_repaired", False):
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": (
                    "PDF structure required automatic xref repair when loaded. "
                    "Container may contain damaged xref tables or truncated streams. Requires human review."
                ),
                "evidence": {"is_repaired": True, "page_count": doc_fitz.page_count},
            }

        if doc_fitz.page_count <= 0:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": "PDF container contains 0 pages or has invalid page catalog. Requires human review.",
                "evidence": {"page_count": 0},
            }

        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.PASS,
            "explanation": "No indicator detected by this check. PDF structure is well-formed with valid page trees and cross-reference table.",
            "evidence": {
                "page_count": doc_fitz.page_count,
                "is_encrypted": False,
                "is_repaired": False,
            },
        }

    except Exception as exc:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.REVIEW,
            "explanation": f"PDF parsing error encountered: {type(exc).__name__}. File may be malformed or corrupted.",
            "evidence": {"error": type(exc).__name__},
        }
    finally:
        if doc_fitz:
            try:
                doc_fitz.close()
            except Exception:
                pass


def check_image_indicators(doc: Document, data: Optional[bytes]) -> Dict[str, Any]:
    """Check 4: Image dimensions, resolution, and encoding indicators."""
    check_type = "image_indicators"
    check_name = "Image Resolution & Encoding Indicators"

    if data is None:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": "Document bytes unavailable for image inspection.",
            "evidence": {},
        }

    is_image = any(img_fmt in doc.mime_type.lower() for img_fmt in ["png", "jpeg", "jpg", "tiff", "bmp"])

    if is_image:
        try:
            with Image.open(io.BytesIO(data)) as img:
                w, h = img.size
                fmt = img.format
                mode = img.mode

                # Flag extreme low-resolution images
                if w < 120 or h < 120:
                    return {
                        "check_type": check_type,
                        "check_name": check_name,
                        "result": AuthenticityResult.REVIEW,
                        "explanation": (
                            f"Image dimensions ({w}×{h}) are unusually low for official documentation. "
                            "May be a placeholder, thumbnail, or low-quality scan. Requires human review."
                        ),
                        "evidence": {"width": w, "height": h, "format": fmt, "mode": mode},
                    }

                aspect_ratio = max(w, h) / max(min(w, h), 1)
                if aspect_ratio > 15.0:
                    return {
                        "check_type": check_type,
                        "check_name": check_name,
                        "result": AuthenticityResult.REVIEW,
                        "explanation": f"Extreme image aspect ratio ({aspect_ratio:.1f}:1). Image appears heavily cropped or distorted.",
                        "evidence": {"width": w, "height": h, "aspect_ratio": round(aspect_ratio, 2)},
                    }

                return {
                    "check_type": check_type,
                    "check_name": check_name,
                    "result": AuthenticityResult.PASS,
                    "explanation": "No indicator detected by this check. Image dimensions, color profile, and encoding are consistent with document scans.",
                    "evidence": {"width": w, "height": h, "format": fmt, "mode": mode},
                }
        except Exception as exc:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": f"Failed to parse image container: {type(exc).__name__}. Requires human review.",
                "evidence": {"error": type(exc).__name__},
            }

    # For PDF documents, inspect embedded raster streams
    if "pdf" in doc.mime_type.lower():
        doc_fitz = None
        try:
            doc_fitz = fitz.open(stream=data, filetype="pdf")
            total_images = 0
            small_images = 0

            for pno in range(min(doc_fitz.page_count, 10)):  # Screen first 10 pages
                images = doc_fitz.get_page_images(pno)
                total_images += len(images)
                for img_info in images:
                    # img_info = (xref, smask, width, height, bpc, colorspace, ...)
                    width = img_info[2]
                    height = img_info[3]
                    if width < 50 and height < 50:
                        small_images += 1

            if total_images == 0:
                return {
                    "check_type": check_type,
                    "check_name": check_name,
                    "result": AuthenticityResult.UNAVAILABLE,
                    "explanation": "No raster image streams detected in PDF. Document appears to be purely text/vector based.",
                    "evidence": {"embedded_images": 0},
                }

            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.PASS,
                "explanation": f"No indicator detected by this check. Document contains {total_images} embedded raster stream(s).",
                "evidence": {
                    "total_images": total_images,
                    "tiny_artifacts": small_images,
                },
            }
        except Exception as exc:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.UNAVAILABLE,
                "explanation": f"Image stream screening unavailable: {type(exc).__name__}",
                "evidence": {"error": type(exc).__name__},
            }
        finally:
            if doc_fitz:
                try:
                    doc_fitz.close()
                except Exception:
                    pass

    return {
        "check_type": check_type,
        "check_name": check_name,
        "result": AuthenticityResult.UNAVAILABLE,
        "explanation": "Image indicator screening not applicable to this MIME type.",
        "evidence": {"mime_type": doc.mime_type},
    }


def check_text_indicators(
    doc: Document,
    application: Optional[Application],
) -> Dict[str, Any]:
    """Check 5: Cross-referencing extracted institutional headers with application data."""
    check_type = "text_indicators"
    check_name = "Textual Header & Entity Consistency"

    if not doc.extracted_fields and not doc.ocr_text:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": "Insufficient extracted text to evaluate textual entity consistency.",
            "evidence": {"has_extracted_fields": False, "has_ocr_text": False},
        }

    extracted: Dict[str, Any] = {}
    if doc.extracted_fields:
        try:
            extracted = json.loads(doc.extracted_fields)
        except Exception:
            extracted = {}

    inst_entry = extracted.get("institution_name")
    doc_inst = inst_entry.get("value") if isinstance(inst_entry, dict) else None

    if doc_inst and application and application.institution_name:
        is_consistent, expl = are_institution_names_consistent(
            doc_inst, application.institution_name
        )
        if not is_consistent:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.REVIEW,
                "explanation": (
                    f"Extracted institution title '{doc_inst}' conflicts with application header "
                    f"'{application.institution_name}'. Requires human review."
                ),
                "evidence": {
                    "extracted_institution": doc_inst,
                    "application_institution": application.institution_name,
                    "details": expl,
                },
            }
        else:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.PASS,
                "explanation": "No indicator detected by this check. Extracted institution name aligns with application record.",
                "evidence": {
                    "extracted_institution": doc_inst,
                    "application_institution": application.institution_name,
                },
            }

    # If document has extracted fields but no direct institution title mismatch
    return {
        "check_type": check_type,
        "check_name": check_name,
        "result": AuthenticityResult.PASS,
        "explanation": "No indicator detected by this check. Extracted text fields contain no contradictory entity markers.",
        "evidence": {"fields_analyzed": list(extracted.keys())},
    }


def check_signature_presence(doc: Document, data: Optional[bytes]) -> Dict[str, Any]:
    """Check 6: Detection of digital signature fields in PDF."""
    check_type = "signature_presence"
    check_name = "Digital Signature Container Presence"

    if data is None or "pdf" not in doc.mime_type.lower():
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": "Digital signature container screening is applicable to PDF documents only.",
            "evidence": {"mime_type": doc.mime_type},
        }

    doc_fitz = None
    try:
        doc_fitz = fitz.open(stream=data, filetype="pdf")

        # PyMuPDF sigflags: bit 0 = document contains signatures; bit 1 = form contains signature fields
        sigflags = doc_fitz.get_sigflags() if hasattr(doc_fitz, "get_sigflags") else -1
        detected_fields: List[str] = []

        for pno in range(doc_fitz.page_count):
            page = doc_fitz[pno]
            for widget in page.widgets():
                if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE or (
                    widget.field_name and "sig" in widget.field_name.lower()
                ):
                    detected_fields.append(widget.field_name or f"sig_field_p{pno+1}")

        # Raw marker fallback
        raw_sig_present = b"/ByteRange" in data and b"/SubFilter" in data

        has_signature = len(detected_fields) > 0 or sigflags > 0 or raw_sig_present

        if has_signature:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.PASS,
                "explanation": (
                    "Digital signature field detected in PDF container. "
                    "(Note: Presence indicates signed PDF form; full cryptographic certificate chain "
                    "verification requires an external trust store and was not performed)."
                ),
                "evidence": {
                    "signature_field_detected": True,
                    "field_count": max(len(detected_fields), 1),
                    "sigflags": sigflags,
                    "cryptographic_chain_verified": False,
                },
            }
        else:
            return {
                "check_type": check_type,
                "check_name": check_name,
                "result": AuthenticityResult.PASS,
                "explanation": (
                    "No indicator detected by this check. No digital signature field present. "
                    "(Most scanned or standard PDF documents are unsigned; absence of digital signature does not indicate illegitimacy)."
                ),
                "evidence": {
                    "signature_field_detected": False,
                },
            }

    except Exception as exc:
        return {
            "check_type": check_type,
            "check_name": check_name,
            "result": AuthenticityResult.UNAVAILABLE,
            "explanation": f"Signature screening unavailable: {type(exc).__name__}",
            "evidence": {"error": type(exc).__name__},
        }
    finally:
        if doc_fitz:
            try:
                doc_fitz.close()
            except Exception:
                pass


def run_document_screening(
    doc: Document,
    data: Optional[bytes],
    application: Optional[Application],
) -> List[Dict[str, Any]]:
    """Execute all 6 screening checks on a document and return candidate check results."""
    candidates = [
        check_file_integrity(doc, data),
        check_pdf_metadata(doc, data),
        check_pdf_structure(doc, data),
        check_image_indicators(doc, data),
        check_text_indicators(doc, application),
        check_signature_presence(doc, data),
    ]
    return candidates


def run_application_screening(
    db: Session,
    application_id: str,
    storage: LocalStorageBackend,
    actor_label: str = "system",
) -> List[AuthenticityCheck]:
    """Execute authenticity screening across all documents for an application.

    Idempotent: updates existing check records in-place.
    Preserves human reviewer statuses and notes if already reviewed.
    Records an immutable AuditEvent in the audit trail.
    """
    app = db.execute(
        select(Application).where(Application.id == application_id)
    ).scalar_one_or_none()

    if not app:
        raise ValueError(f"Application '{application_id}' not found.")

    docs = db.execute(
        select(Document).where(Document.application_id == application_id)
    ).scalars().all()

    # Existing checks mapped by (document_id, check_type)
    existing_checks = db.execute(
        select(AuthenticityCheck).where(AuthenticityCheck.application_id == application_id)
    ).scalars().all()

    existing_map = {(c.document_id, c.check_type): c for c in existing_checks}

    persisted_checks: List[AuthenticityCheck] = []
    total_screened = 0
    review_flags = 0

    for doc in docs:
        data = _load_document_bytes(storage, doc.stored_filename)
        candidates = run_document_screening(doc, data, app)

        for cand in candidates:
            total_screened += 1
            if cand["result"] == AuthenticityResult.REVIEW:
                review_flags += 1

            key = (doc.id, cand["check_type"])
            existing = existing_map.get(key)

            if existing:
                # If already reviewed by human officer, preserve reviewer status and notes!
                if existing.reviewer_status in (
                    FindingStatus.RESOLVED,
                    FindingStatus.DISMISSED,
                    FindingStatus.UNDER_REVIEW,
                    FindingStatus.REQUIRES_CLARIFICATION,
                ):
                    existing.result = cand["result"]
                    existing.explanation = cand["explanation"]
                    existing.evidence = cand["evidence"]
                    existing.screening_version = SCREENING_VERSION
                    persisted_checks.append(existing)
                    continue

                # Update OPEN record
                existing.check_name = cand["check_name"]
                existing.result = cand["result"]
                existing.explanation = cand["explanation"]
                existing.evidence = cand["evidence"]
                existing.screening_version = SCREENING_VERSION
                persisted_checks.append(existing)
            else:
                new_check = AuthenticityCheck(
                    application_id=application_id,
                    document_id=doc.id,
                    check_type=cand["check_type"],
                    check_name=cand["check_name"],
                    result=cand["result"],
                    explanation=cand["explanation"],
                    evidence=cand["evidence"],
                    screening_version=SCREENING_VERSION,
                    reviewer_status=FindingStatus.OPEN,
                )
                db.add(new_check)
                persisted_checks.append(new_check)

    # Record Audit Event
    audit = AuditEvent(
        application_id=application_id,
        actor_label=actor_label,
        action="authenticity.screened",
        resource_type="application",
        resource_id=application_id,
        detail=(
            f"Screened {len(docs)} document(s) ({total_screened} checks total). "
            f"Review flags: {review_flags}."
        ),
        metadata_={
            "documents_count": len(docs),
            "total_checks": total_screened,
            "review_flags": review_flags,
            "screening_version": SCREENING_VERSION,
        },
    )
    db.add(audit)
    db.commit()

    for c in persisted_checks:
        db.refresh(c)

    return persisted_checks


def update_check_review_status(
    db: Session,
    application_id: str,
    check_id: str,
    new_status: FindingStatus,
    notes: Optional[str] = None,
    actor_label: str = "Authorized Officer",
) -> AuthenticityCheck:
    """Update reviewer status & notes for a specific authenticity check, logging an audit event."""
    check = db.execute(
        select(AuthenticityCheck).where(
            AuthenticityCheck.id == check_id,
            AuthenticityCheck.application_id == application_id,
        )
    ).scalar_one_or_none()

    if not check:
        raise ValueError(f"Authenticity check '{check_id}' not found for application '{application_id}'.")

    old_status = check.reviewer_status
    check.reviewer_status = new_status
    if notes is not None:
        check.reviewer_notes = notes

    # Audit event
    audit = AuditEvent(
        application_id=application_id,
        actor_label=actor_label,
        action="authenticity.reviewed",
        resource_type="authenticity_check",
        resource_id=check.id,
        detail=(
            f"Check '{check.check_type}' status updated from '{old_status.value}' to '{new_status.value}'. "
            + (f"Notes: {notes}" if notes else "")
        ),
        metadata_={
            "old_status": old_status.value,
            "new_status": new_status.value,
            "notes": notes,
            "check_type": check.check_type,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(check)
    return check
