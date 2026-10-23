"""OCR engine — extracts text from documents page by page.

Strategy:
  1. For PDFs: use PyMuPDF to extract embedded text first.
     If a page yields < MIN_CHARS characters of embedded text,
     fall back to Tesseract OCR on a rendered page image (if available).
  2. For images (PNG, JPEG, TIFF): use Tesseract OCR (if available).

Tesseract is an *optional* runtime dependency. If the binary is not found,
image OCR returns an empty string and an explanatory warning is logged.
No exception is raised — embedded PDF extraction still works.
"""
import io
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Minimum embedded-text characters before we try OCR on a PDF page.
MIN_EMBEDDED_CHARS = 30


@dataclass
class PageText:
    """Text extracted from a single page."""
    page_number: int          # 1-indexed
    text: str                 # Extracted text (may be empty)
    source: str               # "embedded" | "ocr" | "none"


@dataclass
class ExtractionResult:
    """Full extraction result for one document."""
    pages: list[PageText] = field(default_factory=list)
    full_text: str = ""       # All pages concatenated
    error: Optional[str] = None   # Set if extraction failed entirely


def resolve_tesseract_cmd(cmd: str = "tesseract") -> Optional[str]:
    """Resolve the Tesseract binary path.

    Checks:
      1. Directly if `cmd` is an existing file path.
      2. Via system PATH (`shutil.which`).
      3. Standard Windows installation paths if on Windows.
    Returns the resolved executable path or None if not discoverable.
    """
    if not cmd:
        cmd = "tesseract"

    p = Path(cmd)
    if p.is_file():
        return str(p.resolve())

    found = shutil.which(cmd)
    if found:
        return found

    if sys.platform == "win32":
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
        localapp = os.environ.get("LOCALAPPDATA")
        if localapp:
            candidates.append(Path(localapp) / "Programs" / "Tesseract-OCR" / "tesseract.exe")

        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

    return None


def _try_tesseract_on_image(image_bytes: bytes, tesseract_cmd: str = "tesseract") -> Optional[str]:
    """Run Tesseract on raw image bytes.

    Returns the OCR text, or None if Tesseract is unavailable or fails.
    Does NOT raise — unavailability is handled gracefully.
    """
    resolved_cmd = resolve_tesseract_cmd(tesseract_cmd)
    if not resolved_cmd:
        logger.warning("Tesseract binary could not be resolved (tried '%s')", tesseract_cmd)
        return None

    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        pytesseract.pytesseract.tesseract_cmd = resolved_cmd
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text
    except Exception as exc:
        logger.warning("Tesseract OCR execution failed: %s", exc)
        return None


def extract_from_pdf(
    data: bytes,
    tesseract_cmd: str = "tesseract",
) -> ExtractionResult:
    """Extract text from a PDF byte string page by page.

    For each page:
      - Extract embedded text using PyMuPDF.
      - If the page has < MIN_EMBEDDED_CHARS characters, render it to a PNG
        and attempt Tesseract OCR.
    """
    result = ExtractionResult()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        result.error = f"Cannot open PDF: {exc}"
        logger.error("PDF open failed: %s", exc)
        return result

    ocr_attempted_and_failed = False
    try:
        for i, page in enumerate(doc, start=1):
            embedded = page.get_text("text").strip()

            if len(embedded) >= MIN_EMBEDDED_CHARS:
                result.pages.append(PageText(page_number=i, text=embedded, source="embedded"))
            else:
                # Try Tesseract on a rendered image of the page
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                ocr_text = _try_tesseract_on_image(img_bytes, tesseract_cmd)

                if ocr_text and ocr_text.strip():
                    result.pages.append(
                        PageText(page_number=i, text=ocr_text.strip(), source="ocr")
                    )
                elif embedded:
                    # Small amount of embedded text but below threshold — still use it
                    result.pages.append(PageText(page_number=i, text=embedded, source="embedded"))
                else:
                    result.pages.append(PageText(page_number=i, text="", source="none"))
                    ocr_attempted_and_failed = True
    finally:
        doc.close()

    result.full_text = "\n\n".join(p.text for p in result.pages if p.text).strip()
    if not result.full_text:
        if ocr_attempted_and_failed:
            result.error = (
                "PDF contains no embedded text and Tesseract OCR was unavailable or failed. "
                "Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        else:
            result.error = "PDF contains no readable text."

    return result


def extract_from_image(
    data: bytes,
    mime_type: str,
    tesseract_cmd: str = "tesseract",
) -> ExtractionResult:
    """Extract text from a PNG, JPEG, or TIFF image using Tesseract.

    If Tesseract is unavailable, returns an ExtractionResult with an empty page
    and an actionable error message.
    """
    result = ExtractionResult()
    resolved_cmd = resolve_tesseract_cmd(tesseract_cmd)
    if not resolved_cmd:
        result.pages.append(PageText(page_number=1, text="", source="none"))
        result.error = (
            "Tesseract OCR binary not found. Image text extraction is unavailable. "
            "Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki "
            "and ensure it is in PATH or set TESSERACT_CMD."
        )
        logger.warning("Image OCR skipped — Tesseract unavailable for mime=%s", mime_type)
        return result

    ocr_text = _try_tesseract_on_image(data, resolved_cmd)

    if ocr_text is not None and ocr_text.strip():
        result.pages.append(PageText(page_number=1, text=ocr_text.strip(), source="ocr"))
        result.full_text = ocr_text.strip()
    elif ocr_text is not None:
        result.pages.append(PageText(page_number=1, text="", source="ocr"))
        result.error = "Image was scanned but no readable text was detected."
    else:
        result.pages.append(PageText(page_number=1, text="", source="none"))
        result.error = "Tesseract OCR failed to process the image."

    return result


def run_extraction(
    data: bytes,
    mime_type: str,
    tesseract_cmd: str = "tesseract",
) -> ExtractionResult:
    """Dispatch OCR to the correct extractor based on MIME type."""
    if mime_type == "application/pdf":
        return extract_from_pdf(data, tesseract_cmd=tesseract_cmd)
    elif mime_type in ("image/png", "image/jpeg", "image/tiff"):
        return extract_from_image(data, mime_type=mime_type, tesseract_cmd=tesseract_cmd)
    else:
        result = ExtractionResult()
        result.error = f"Unsupported MIME type for OCR: {mime_type}"
        return result
