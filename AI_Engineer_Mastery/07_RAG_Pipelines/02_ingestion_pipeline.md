# RAG Ingestion Pipeline — Production Document Processing

## Why Ingestion Quality Determines Everything

Your RAG is only as good as its ingestion. Bad extraction → bad chunks → bad embeddings → bad search → bad answers. Most RAG failures trace back to ingestion.

## The Pipeline

```
Document → Parse → Clean → Chunk → Enrich Metadata → Embed → Index → Serve
```

## Document Parsing

| Format | Tool | Gotchas |
|--------|------|---------|
| PDF (text) | PyMuPDF, pdfplumber | Multi-column, headers/footers |
| PDF (scanned) | Tesseract + pdf2image | OCR errors, poor quality |
| DOCX | python-docx | Embedded images not extracted |
| HTML | BeautifulSoup, trafilatura | Boilerplate removal |
| Any | Unstructured.io, Docling | Heavy but handles everything |

## Text Cleaning
Remove: page headers/footers, broken hyphenation, excessive whitespace, boilerplate, encoding issues. Apply: chardet → dehyphenate → collapse whitespace → Unicode NFC.

## Chunking Strategies

| Strategy | Quality | Use When |
|----------|---------|----------|
| Fixed-size | Low | Prototyping only |
| Sentence-aware ⭐ | Good | General RAG |
| Recursive | Good | Mixed documents |
| Semantic | Excellent | Topic-shifting content |
| Parent-child | Excellent | Need precise retrieval + rich context |

## Metadata Enrichment
Every chunk needs: document_id, filename, page_number, chunk_index, heading, owner_id, created_at, content_hash.

## Deduplication
- Document-level: SHA-256 file hash
- Chunk-level: hash each chunk's text
- Semantic: cosine similarity > 0.98 = duplicate

## Idempotent Reprocessing
DELETE existing chunks → reprocess → INSERT new chunks. Use transactions for atomicity. Track chunk strategy version in metadata.
