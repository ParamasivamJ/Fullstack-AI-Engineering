# 02 — Text Extraction Mastery

## Why Text Extraction Is Hard

A PDF is not a text document. It is a **page description language** — it tells
a printer where to draw each glyph on a page. There is no "paragraph" or "sentence"
in a PDF. Just coordinates and glyphs.

A DOCX is a ZIP file containing XML. A table in DOCX is a tree of XML nodes.
A header is styled XML. An image is a binary blob inside the ZIP.

Extracting clean, structured text from these formats is an entire discipline.
Doing it badly means your embeddings are bad, your search is bad, your RAG is bad.

---

## The Extraction Decision Tree

```
What file format?
      │
      ├── .txt
      │     └── Read directly with UTF-8 encoding
      │         Handle encoding errors: errors="replace"
      │
      ├── .pdf
      │     ├── Is it text-based? (selectable text)
      │     │     ├── YES → PyMuPDF (fitz) or pdfplumber
      │     │     │         Fast, accurate, preserves layout
      │     │     └── NO → It's a scanned image PDF
      │     │           └── OCR with Tesseract + pdf2image
      │     │               Slow, less accurate, but the only option
      │     └── Does it have complex tables?
      │           ├── YES → pdfplumber (designed for tables)
      │           └── NO → PyMuPDF (faster general extraction)
      │
      ├── .docx
      │     └── python-docx
      │         Handles paragraphs, tables, headers, footers
      │         Does NOT handle images embedded in DOCX
      │
      └── Complex/mixed (enterprise)
            └── Unstructured.io
                Handles PDF, DOCX, HTML, PPTX, EPUB, Images
                Auto-detects format, extracts everything
                Best quality but heaviest dependency
```

---

## Tool Comparison: PDF Extraction

| Tool | Speed | Table Support | Layout | OCR | Install Size |
|------|-------|-------------|--------|-----|-------------|
| **PyMuPDF (fitz)** | ⚡ Fastest | Basic | Good | Via Tesseract | 15 MB |
| **pdfplumber** | 🐢 Medium | ⭐ Best | Excellent | No | 5 MB |
| **PyPDF2** | ⚡ Fast | None | Poor | No | 1 MB |
| **Unstructured** | 🐢 Slow | Good | Excellent | Built-in | 500+ MB |
| **LlamaParse** | Cloud API | Excellent | Excellent | Yes | API only |
| **Docling (IBM)** | 🐢 Medium | Excellent | Excellent | Yes | 200+ MB |

### Recommendation:
- **For this project:** PyMuPDF (fast + good enough for most PDFs)
- **For enterprise RAG:** Unstructured or Docling (handles everything)
- **For table-heavy PDFs:** pdfplumber

---

## PyMuPDF (fitz) — The Workhorse

```python
import fitz  # pip install PyMuPDF

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extracts text from each page of a PDF.
    Returns a list of dicts with page_number and text.
    """
    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # get_text("text") returns plain text
        # get_text("blocks") returns positioned blocks (for layout awareness)
        # get_text("dict") returns full structure with fonts, sizes, positions
        text = page.get_text("text")

        # Clean up common PDF artifacts
        text = text.strip()
        # Remove excessive blank lines (PDFs often have many)
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)

        if text:  # skip completely empty pages
            pages.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
            })

    doc.close()
    return pages
```

### Advanced: Extract with Layout Awareness

```python
def extract_blocks_from_pdf(file_path: str) -> list[dict]:
    """
    Extracts text BLOCKS instead of raw text.
    Each block has position coordinates — useful for:
    - Detecting headers (larger font, top of page)
    - Detecting footers (bottom of page, repeated text)
    - Detecting columns (left/right position)
    """
    doc = fitz.open(file_path)
    all_blocks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        # Each block: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type: 0 = text, 1 = image

        for b in blocks:
            if b[6] == 0:  # text block only
                all_blocks.append({
                    "page": page_num + 1,
                    "text": b[4].strip(),
                    "x0": b[0], "y0": b[1],  # top-left corner
                    "x1": b[2], "y1": b[3],  # bottom-right corner
                })

    doc.close()
    return all_blocks
```

---

## pdfplumber — For Tables

```python
import pdfplumber  # pip install pdfplumber

def extract_tables_from_pdf(file_path: str) -> list[dict]:
    """
    Extracts tables from a PDF with row/column structure preserved.
    Returns each table as a list of rows (each row is a list of cells).
    """
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract all tables from this page
            page_tables = page.extract_tables()

            for table_idx, table in enumerate(page_tables):
                # table is a list of rows, each row is a list of cell strings
                tables.append({
                    "page": page_num + 1,
                    "table_index": table_idx,
                    "headers": table[0] if table else [],
                    "rows": table[1:] if len(table) > 1 else [],
                    "row_count": len(table) - 1,
                })

            # Also extract the non-table text
            text = page.extract_text()
            # You can filter out table areas to get only the prose text

    return tables
```

---

## python-docx — Word Documents

```python
from docx import Document  # pip install python-docx

def extract_text_from_docx(file_path: str) -> dict:
    """
    Extracts paragraphs and tables from a DOCX file.
    DOCX is XML inside a ZIP — python-docx parses it cleanly.
    """
    doc = Document(file_path)

    # Extract paragraphs
    paragraphs = []
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            paragraphs.append({
                "index": i,
                "text": para.text.strip(),
                "style": para.style.name,  # "Heading 1", "Normal", etc.
                "is_heading": para.style.name.startswith("Heading"),
            })

    # Extract tables
    tables = []
    for t_idx, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        tables.append({
            "table_index": t_idx,
            "headers": rows[0] if rows else [],
            "rows": rows[1:] if len(rows) > 1 else [],
        })

    return {
        "paragraphs": paragraphs,
        "tables": tables,
        "total_paragraphs": len(paragraphs),
        "total_tables": len(tables),
    }
```

---

## Plain Text Files

```python
async def extract_text_from_txt(file_path: str) -> str:
    """
    Reads a plain text file with proper encoding detection.

    Common problem: files claim to be UTF-8 but contain Windows-1252 characters.
    Solution: try UTF-8 first, then fall back to other encodings.
    """
    import chardet  # pip install chardet

    with open(file_path, "rb") as f:
        raw = f.read()

    # Detect encoding from the raw bytes
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = raw.decode("utf-8", errors="replace")

    return text
```

---

## OCR: Handling Scanned PDFs

Some PDFs contain only images — no text layer. You need OCR.

```python
# pip install pytesseract pdf2image Pillow
# Also install Tesseract: https://github.com/tesseract-ocr/tesseract

import pytesseract
from pdf2image import convert_from_path

def extract_text_ocr(file_path: str) -> list[dict]:
    """
    Converts each PDF page to an image, then runs OCR.
    Much slower than direct text extraction but works on scanned documents.
    """
    # Convert PDF pages to PIL images
    images = convert_from_path(file_path, dpi=300)  # 300 DPI for quality OCR

    pages = []
    for page_num, image in enumerate(images):
        # Run Tesseract OCR on each image
        text = pytesseract.image_to_string(image, lang="eng")
        pages.append({
            "page_number": page_num + 1,
            "text": text.strip(),
            "method": "ocr",
        })

    return pages


def is_scanned_pdf(file_path: str) -> bool:
    """
    Detects whether a PDF is scanned (image-only) or has selectable text.
    If the first 3 pages have very little text, it's likely scanned.
    """
    import fitz
    doc = fitz.open(file_path)

    text_chars = 0
    pages_to_check = min(3, len(doc))

    for i in range(pages_to_check):
        text_chars += len(doc[i].get_text("text").strip())

    doc.close()

    # If less than 50 chars across 3 pages, it's probably scanned
    return text_chars < 50
```

---

## Unstructured.io — The Swiss Army Knife

```python
# pip install unstructured[all-docs]

from unstructured.partition.auto import partition

def extract_with_unstructured(file_path: str) -> list[dict]:
    """
    Unstructured auto-detects file type and extracts elements.
    Handles: PDF, DOCX, PPTX, HTML, EPUB, TXT, images.

    Each element has a type: Title, NarrativeText, Table, ListItem, etc.
    This type awareness is extremely useful for intelligent chunking.
    """
    elements = partition(filename=file_path)

    extracted = []
    for element in elements:
        extracted.append({
            "type": type(element).__name__,  # "Title", "NarrativeText", etc.
            "text": str(element),
            "metadata": {
                "page_number": element.metadata.page_number,
                "filename": element.metadata.filename,
            },
        })

    return extracted
```

---

## Text Cleaning Pipeline

After extraction, the raw text is messy. Clean it before chunking.

```python
import re

def clean_extracted_text(text: str) -> str:
    """
    Cleans common artifacts from PDF/DOCX extraction.
    Apply this BEFORE chunking.
    """
    # 1. Remove page numbers and headers/footers (common patterns)
    text = re.sub(r"^\s*Page \d+ of \d+\s*$", "", text, flags=re.MULTILINE)

    # 2. Fix broken words from line wrapping
    #    "imple-\nmentation" → "implementation"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # 3. Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 4. Remove excessive whitespace within lines
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 5. Strip leading/trailing whitespace
    text = text.strip()

    return text
```

---

## Comparison of All Alternatives

| Scenario | Best Tool | Why |
|----------|-----------|-----|
| Fast PDF extraction | PyMuPDF | Fastest, C-based library |
| PDF with complex tables | pdfplumber | Purpose-built table detection |
| Word documents | python-docx | Native DOCX parser |
| Scanned/image PDFs | Tesseract OCR | Open-source OCR engine |
| Enterprise (any format) | Unstructured.io | Handles everything |
| Best table+layout accuracy | Docling (IBM) | ML-based structure detection |
| Cloud API (zero infra) | LlamaParse | Send PDF, get structured text |
| Google Docs/Sheets | Google Drive API | Native API access |
