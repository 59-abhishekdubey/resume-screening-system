# Library choice: pdfplumber (over pypdf / PyMuPDF)
# - pdfplumber is built on pdfminer.six + pypdfium2. It preserves reading order
#   better than pypdf for multi-column resume layouts and exposes per-page
#   extract_text() with layout-aware fallback. pypdf is lighter but loses
#   column order more often.
# - No OCR is used. Image-only pages have no extractable text objects, so
#   extract_text() returns None and we return "" with a warning (out of scope).
# - Heavy OCR deps (pytesseract, easyocr, etc.) are NOT imported.
import logging
import os

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: str) -> str:
    """Extract raw text from a single PDF resume.

    Args:
        path: Path to a PDF file on disk.

    Returns:
        str: Concatenated text from all pages joined by newline. Returns ""
        for encrypted PDFs or image-only pages (no extractable text objects)
        and logs a warning to stderr. Never attempts OCR.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        with pdfplumber.open(path) as pdf:
            # pdfplumber signals encryption via an attribute and/or exception,
            # not via text content. Check both possible locations.
            if getattr(pdf, "is_encrypted", False):
                logger.warning("Encrypted PDF (password required): %s", path)
                return ""
            doc = getattr(pdf, "doc", None)
            if doc is not None and getattr(doc, "is_encrypted", False):
                logger.warning("Encrypted PDF (password required): %s", path)
                return ""

            text_parts: list[str] = []
            for page in pdf.pages:
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text.strip())
                except Exception:
                    continue

            full_text = "\n".join(text_parts).strip()

            if not full_text:
                logger.warning("No extractable text from PDF (image-only?): %s", path)
                return ""

            return full_text

    except FileNotFoundError:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "password" in msg or "encrypt" in msg:
            logger.warning("Encrypted PDF (password required): %s", path)
            return ""
        exc_name = type(exc).__name__.lower()
        if "password" in exc_name or "encrypt" in exc_name:
            logger.warning("Encrypted PDF (password required): %s", path)
            return ""
        logger.warning("Could not read PDF: %s (%s)", path, exc)
        return ""


def extract_text_from_pdfs(folder: str) -> dict[str, str]:
    """Extract text from all PDFs in a folder.

    Args:
        folder: Path to a directory. Non-existent directory returns {}.

    Returns:
        dict[str, str]: Mapping of filename without extension -> extracted text.
        Returns {} if the folder is empty, does not exist, or contains no PDFs.
        Encrypted / image-only PDFs map to "".
    """
    results: dict[str, str] = {}
    if not os.path.isdir(folder):
        return results

    pdf_files = sorted(
        f for f in os.listdir(folder) if f.lower().endswith(".pdf")
    )

    for filename in pdf_files:
        path = os.path.join(folder, filename)
        name = os.path.splitext(filename)[0]
        text = extract_text_from_pdf(path)
        results[name] = text

    return results
