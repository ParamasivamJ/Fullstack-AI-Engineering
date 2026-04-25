"""
Template: Text Extraction from PDF, DOCX, and TXT
===================================================
Run standalone to test extraction on your own files:
  python extraction_demo.py sample.pdf
  python extraction_demo.py report.docx
  python extraction_demo.py notes.txt
"""

import sys
import re
from pathlib import Path


# ─── PDF EXTRACTION ──────────────────────────────────────────────

def extract_pdf(file_path: str) -> list[dict]:
    """Extracts text from each page of a PDF using PyMuPDF."""
    import fitz  # pip install PyMuPDF

    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive blank lines

        if text:
            pages.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
            })

    doc.close()
    print(f"  ✅ Extracted {len(pages)} pages from PDF")
    return pages


# ─── DOCX EXTRACTION ────────────────────────────────────────────

def extract_docx(file_path: str) -> list[dict]:
    """Extracts paragraphs from a DOCX file using python-docx."""
    from docx import Document  # pip install python-docx

    doc = Document(file_path)
    pages = []
    current_text = []
    page_num = 1

    for para in doc.paragraphs:
        if para.text.strip():
            current_text.append(para.text.strip())

        # Approximate page breaks (DOCX doesn't have hard page boundaries)
        # Group every ~3000 chars as a "page" for chunking purposes
        combined = "\n".join(current_text)
        if len(combined) > 3000:
            pages.append({
                "page_number": page_num,
                "text": combined,
                "char_count": len(combined),
            })
            current_text = []
            page_num += 1

    # Don't forget remaining text
    if current_text:
        combined = "\n".join(current_text)
        pages.append({
            "page_number": page_num,
            "text": combined,
            "char_count": len(combined),
        })

    print(f"  ✅ Extracted {len(pages)} sections from DOCX")
    return pages


# ─── TXT EXTRACTION ─────────────────────────────────────────────

def extract_txt(file_path: str) -> list[dict]:
    """Reads a plain text file with encoding detection."""
    with open(file_path, "rb") as f:
        raw = f.read()

    # Try UTF-8 first, fallback to latin-1
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    print(f"  ✅ Read {len(text)} characters from TXT")
    return [{"page_number": 1, "text": text.strip(), "char_count": len(text)}]


# ─── TEXT CLEANING ───────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Cleans common artifacts from extracted text."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)     # fix hyphenated line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)            # collapse blank lines
    text = re.sub(r"[ \t]{2,}", " ", text)            # collapse spaces
    text = re.sub(r"^\s*Page \d+.*$", "", text, flags=re.MULTILINE)  # remove page numbers
    return text.strip()


# ─── DISPATCHER ──────────────────────────────────────────────────

EXTRACTORS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".txt": extract_txt,
}

def extract_text(file_path: str) -> list[dict]:
    """Dispatches to the correct extractor based on file extension."""
    ext = Path(file_path).suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(EXTRACTORS.keys())}")

    pages = extractor(file_path)

    # Clean all extracted text
    for page in pages:
        page["text"] = clean_text(page["text"])

    return pages


# ─── CLI DEMO ────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extraction_demo.py <file_path>")
        print("  Supports: .pdf, .docx, .txt")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"\n📄 Extracting text from: {file_path}")

    pages = extract_text(file_path)

    total_chars = sum(p["char_count"] for p in pages)
    print(f"\n📊 Results:")
    print(f"   Pages/Sections: {len(pages)}")
    print(f"   Total characters: {total_chars:,}")
    print(f"\n── First 500 chars of page 1 ──")
    print(pages[0]["text"][:500] if pages else "(no text)")
