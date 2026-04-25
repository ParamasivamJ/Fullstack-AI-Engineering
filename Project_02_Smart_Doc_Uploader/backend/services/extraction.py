"""
Project 02 — Service: Text Extraction
=======================================
Extracts text from PDF, DOCX, and TXT files.
"""

import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def extract_text(file_path: str, content_type: str) -> list[dict]:
    """
    Dispatches to the correct extractor based on content type.
    Returns a list of {"page_number": int, "text": str}.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf" or content_type == "application/pdf":
        return _extract_pdf(file_path)
    elif ext == ".docx" or content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        return _extract_docx(file_path)
    elif ext == ".txt" or content_type.startswith("text/"):
        return _extract_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext} ({content_type})")


def _extract_pdf(file_path: str) -> list[dict]:
    """Extracts text per page from a PDF using PyMuPDF."""
    import fitz

    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()
        text = _clean_text(text)
        if text and len(text) > 10:  # skip near-empty pages
            pages.append({"page_number": page_num + 1, "text": text})

    doc.close()
    logger.info(f"PDF extraction: {len(pages)} pages from {file_path}")
    return pages


def _extract_docx(file_path: str) -> list[dict]:
    """Extracts paragraphs from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    pages = []
    current_text = []
    page_num = 1

    for para in doc.paragraphs:
        if para.text.strip():
            current_text.append(para.text.strip())

        combined = "\n".join(current_text)
        if len(combined) > 3000:
            pages.append({"page_number": page_num, "text": _clean_text(combined)})
            current_text = []
            page_num += 1

    if current_text:
        combined = "\n".join(current_text)
        if combined.strip():
            pages.append({"page_number": page_num, "text": _clean_text(combined)})

    logger.info(f"DOCX extraction: {len(pages)} sections from {file_path}")
    return pages


def _extract_txt(file_path: str) -> list[dict]:
    """Reads a plain text file with encoding fallback."""
    with open(file_path, "rb") as f:
        raw = f.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    text = _clean_text(text)
    logger.info(f"TXT extraction: {len(text)} chars from {file_path}")
    return [{"page_number": 1, "text": text}]


def _clean_text(text: str) -> str:
    """Cleans common extraction artifacts."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s*Page \d+.*$", "", text, flags=re.MULTILINE)
    return text.strip()
