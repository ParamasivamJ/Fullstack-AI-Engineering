# 07 — Full Pipeline Architecture: Ingestion to Search

## The Two Pipelines

Every document search system has exactly two pipelines:

1. **Ingestion Pipeline** — runs ONCE per document upload (write path)
2. **Search Pipeline** — runs on EVERY user query (read path)

The ingestion pipeline is slow and expensive (extract, chunk, embed).
The search pipeline must be fast and cheap (embed query, search index, return).

---

## Pipeline 1: Document Ingestion (Write Path)

```
User uploads a file
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /documents/upload                                         │
│  ├── Validate file (type, size, magic bytes)                    │
│  ├── Stream file to disk/S3                                     │
│  ├── Create Document record (status="uploaded")                 │
│  ├── Return 201 {"id": "...", "status": "uploaded"}             │
│  └── Trigger background task: process_document(doc_id)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Background (async)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  process_document(doc_id)                                       │
│                                                                 │
│  1. UPDATE status → "processing"                                │
│                                                                 │
│  2. EXTRACT TEXT                                                │
│     ├── PDF → PyMuPDF (fitz)                                    │
│     ├── DOCX → python-docx                                      │
│     └── TXT → UTF-8 read with chardet fallback                  │
│                                                                 │
│  3. CLEAN TEXT                                                  │
│     ├── Remove page headers/footers                             │
│     ├── Fix broken words from line wrapping                     │
│     └── Collapse whitespace                                     │
│                                                                 │
│  4. CHUNK TEXT                                                  │
│     ├── Sentence-aware splitting (512 chars, 2-sentence overlap)│
│     └── Attach metadata: page_number, chunk_index, heading      │
│                                                                 │
│  5. GENERATE EMBEDDINGS                                         │
│     ├── Batch encode all chunks: model.encode(texts)            │
│     └── 1000 chunks ≈ 3 seconds on CPU                          │
│                                                                 │
│  6. STORE IN DATABASE                                           │
│     ├── INSERT chunks + embeddings into document_chunks table   │
│     └── Batch insert for performance                            │
│                                                                 │
│  7. UPDATE status → "indexed"                                   │
│     └── On error: status → "failed", log the error              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Error Handling in the Pipeline

```python
async def process_document(doc_id: str, db: AsyncSession):
    doc = await crud.get_document(db, doc_id)
    if not doc:
        return

    try:
        # Update status
        doc.status = "processing"
        await db.commit()

        # Step 2: Extract
        pages = extract_text(doc.storage_path, doc.content_type)

        if not pages:
            doc.status = "failed"
            doc.error_message = "No text could be extracted from this document"
            await db.commit()
            return

        # Step 3: Clean
        cleaned_pages = [clean_text(p["text"]) for p in pages]

        # Step 4: Chunk
        all_chunks = []
        for page in pages:
            chunks = sentence_aware_chunks(page["text"], max_chunk_size=512)
            for idx, chunk_text in enumerate(chunks):
                all_chunks.append({
                    "content": chunk_text,
                    "page_number": page["page_number"],
                    "chunk_index": len(all_chunks),
                })

        # Step 5: Embed (batch for speed)
        texts = [c["content"] for c in all_chunks]
        embeddings = embedding_model.encode(texts, batch_size=64)

        # Step 6: Store
        for chunk_data, embedding in zip(all_chunks, embeddings):
            await crud.create_chunk(
                db=db,
                document_id=doc_id,
                content=chunk_data["content"],
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                embedding=embedding.tolist(),
            )

        # Step 7: Done
        doc.status = "indexed"
        doc.chunk_count = len(all_chunks)
        await db.commit()

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)[:500]
        await db.commit()
        logger.error(f"Document processing failed: {doc_id}", exc_info=True)
```

---

## Pipeline 2: Semantic Search (Read Path)

```
User enters a search query
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /search                                                   │
│  {"query": "How does FastAPI handle auth?", "top_k": 5}         │
│                                                                 │
│  1. EMBED THE QUERY                                             │
│     └── query_vec = model.encode(query)                         │
│         This uses the SAME model used during ingestion           │
│                                                                 │
│  2. APPLY METADATA FILTERS                                       │
│     └── WHERE owner_id = current_user.id                        │
│         AND content_type IN ('application/pdf')                  │
│         AND created_at > '2024-01-01'                            │
│                                                                 │
│  3. VECTOR SEARCH                                               │
│     └── ORDER BY embedding <=> query_vec                        │
│         WHERE similarity > threshold                            │
│         LIMIT top_k                                             │
│                                                                 │
│  4. FORMAT RESULTS                                              │
│     └── Return: content, document_name, page_number, score      │
│         Include source citations for the UI                      │
│                                                                 │
│  Response time target: < 200ms                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Design (All Endpoints)

```
POST   /documents/upload          Upload a file → returns document metadata
GET    /documents                 List current user's documents (with status)
GET    /documents/{id}            Get document details (including chunk count)
GET    /documents/{id}/status     Check processing status
DELETE /documents/{id}            Delete document and all its chunks

POST   /search                    Semantic search across all user's documents
POST   /search/document/{id}      Search within a specific document
GET    /search/suggest            Auto-complete suggestions (optional)

GET    /health                    System health check
```

---

## Database Schema Summary

```
┌──────────────────┐         ┌──────────────────────────┐
│     documents     │         │    document_chunks        │
├──────────────────┤         ├──────────────────────────┤
│ id (UUID PK)     │◄────────│ document_id (FK)          │
│ filename         │   1:N   │ id (UUID PK)              │
│ content_type     │         │ content (TEXT)             │
│ file_size_bytes  │         │ embedding (VECTOR(384))    │
│ storage_path     │         │ page_number (INT)          │
│ status           │         │ chunk_index (INT)          │
│ chunk_count      │         │ created_at                 │
│ error_message    │         └──────────────────────────┘
│ owner_id (FK)    │
│ created_at       │
└──────────────────┘
```

---

## Production Considerations

### 1. Idempotent Processing
If the background task crashes mid-way and retries, it should not create
duplicate chunks. Delete existing chunks before reprocessing:

```python
# Before Step 4-6, delete any existing chunks for this document
await crud.delete_chunks_by_document(db, doc_id)
```

### 2. Concurrent Upload Limiting
Don't let one user trigger 50 document processing jobs simultaneously:

```python
# Check how many documents are currently processing
processing_count = await crud.count_documents_by_status(db, owner_id, "processing")
if processing_count >= 3:
    raise HTTPException(429, "Maximum 3 documents can be processed at once")
```

### 3. Document Size → Processing Time Estimates

| Document | Pages | Chunks | Embed Time (CPU) | Total Time |
|----------|-------|--------|-------------------|-----------|
| 5-page PDF | 5 | ~20 | ~0.3s | ~2s |
| 50-page report | 50 | ~200 | ~1s | ~5s |
| 300-page book | 300 | ~1200 | ~5s | ~15s |
| 1000-page manual | 1000 | ~4000 | ~15s | ~45s |

For large documents (>100 pages), consider Celery instead of BackgroundTasks.

### 4. Storage Cleanup
When a document is deleted, also delete:
- All chunks (CASCADE in SQL)
- The stored file (disk/S3)
- Any cached search results

---

## Tech Stack for This Project

| Component | Tool | Why |
|-----------|------|-----|
| API Framework | FastAPI | Async, auto-docs, Pydantic validation |
| Database | PostgreSQL 16 + pgvector | Relational + vector in one DB |
| ORM | SQLAlchemy 2 (async) | Type-safe, production-standard |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Free, local, fast |
| PDF Extraction | PyMuPDF (fitz) | Fastest Python PDF library |
| DOCX Extraction | python-docx | Standard DOCX parser |
| Chunking | Custom sentence-aware | Tuned for our embedding model |
| Background Jobs | FastAPI BackgroundTasks | Simple, no Redis needed |
| File Storage | Local disk (dev), S3 (prod) | Start simple, scale later |
