# Project 02 — Smart Document Uploader with Semantic Search

Upload PDF, DOCX, or TXT documents and search them by **meaning** — not just keywords.

## What This Project Does

1. **Upload** any PDF, DOCX, or TXT file
2. **Automatic processing** in the background:
   - Extracts text from the document
   - Splits into intelligent chunks (sentence-aware)
   - Generates embedding vectors using AI (all-MiniLM-L6-v2)
   - Stores everything in PostgreSQL + pgvector
3. **Semantic search** — ask a question in plain English, get the most relevant passages with citations

## Architecture

```
                    ┌─────────────────────┐
                    │    FastAPI Backend   │
                    ├─────────────────────┤
   Upload ─────►   │  POST /documents    │   ──► Background:
                    │                     │       Extract → Chunk → Embed → Store
   Search ─────►   │  POST /search       │   ──► Embed query → pgvector search
                    │                     │       ──► Return results + citations
   Status ─────►   │  GET /documents/{id} │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │  PostgreSQL 16      │
                    │  + pgvector         │
                    │                     │
                    │  documents table    │
                    │  document_chunks    │
                    │  (with VECTOR(384)) │
                    └─────────────────────┘
```

## Tech Stack

| Component | Tool |
|-----------|------|
| API Framework | FastAPI (async) |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2 (async) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| PDF Extraction | PyMuPDF (fitz) |
| DOCX Extraction | python-docx |
| Background Jobs | FastAPI BackgroundTasks |

## Quick Start

### 1. Start PostgreSQL with pgvector

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_DB=docuploader \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppass \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 2. Set up the backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run the server
uvicorn main:app --reload
```

### 3. Use the API

Open http://localhost:8000/docs for the interactive API documentation.

**Upload a document:**
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@your_document.pdf"
```

**Check processing status:**
```bash
curl http://localhost:8000/documents/{document_id}/status
```

**Search your documents:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is dependency injection?", "top_k": 5}'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload a document for indexing |
| GET | `/documents` | List all documents |
| GET | `/documents/{id}` | Get document details |
| GET | `/documents/{id}/status` | Check processing status |
| DELETE | `/documents/{id}` | Delete document and chunks |
| POST | `/search` | Semantic search across documents |
| GET | `/health` | System health check |

## Learning Resources

The `Learning/` folder contains 7 deep-dive guides and 4 runnable templates:

| Guide | What You'll Learn |
|-------|------------------|
| `01_file_ingestion_deep_dive.md` | Streaming uploads, magic bytes, S3, security |
| `02_text_extraction_mastery.md` | PyMuPDF, pdfplumber, python-docx, OCR, Unstructured |
| `03_chunking_strategies.md` | 6 strategies: fixed, sentence, recursive, semantic, structure, parent-child |
| `04_embeddings_explained.md` | How vectors work, models, similarity metrics, performance |
| `05_vector_search_mastery.md` | pgvector, HNSW vs IVFFlat, Qdrant, quality metrics |
| `06_metadata_filtering.md` | Pre-filter, hybrid search, RRF, BM25+vector |
| `07_full_pipeline_architecture.md` | End-to-end ingestion and search pipeline design |

Run the templates standalone to experiment:
```bash
cd Learning/templates
python extraction_demo.py your_file.pdf
python chunking_demo.py
python embedding_demo.py
python vector_search_demo.py
```

## Project Structure

```
Project_02_Smart_Doc_Uploader/
├── README.md
├── Learning/                        # 📚 Deep-dive guides + templates
│   ├── 01_file_ingestion_deep_dive.md
│   ├── 02_text_extraction_mastery.md
│   ├── 03_chunking_strategies.md
│   ├── 04_embeddings_explained.md
│   ├── 05_vector_search_mastery.md
│   ├── 06_metadata_filtering.md
│   ├── 07_full_pipeline_architecture.md
│   └── templates/
│       ├── extraction_demo.py
│       ├── chunking_demo.py
│       ├── embedding_demo.py
│       └── vector_search_demo.py
└── backend/                         # 🔧 FastAPI application
    ├── main.py                      # App factory + lifespan
    ├── config.py                    # Settings from .env
    ├── database.py                  # Async engine + pgvector setup
    ├── models.py                    # SQLAlchemy models (Document, Chunk)
    ├── schemas.py                   # Pydantic request/response schemas
    ├── crud.py                      # All database queries
    ├── services/
    │   ├── extraction.py            # PDF/DOCX/TXT text extraction
    │   ├── chunking.py              # Sentence-aware chunking
    │   ├── embedding.py             # sentence-transformers wrapper
    │   └── search.py                # Search pipeline orchestration
    ├── routers/
    │   ├── documents.py             # Upload, list, delete endpoints
    │   └── search.py                # Semantic search endpoint
    ├── requirements.txt
    └── .env.example
```

## Skills You Build

- ✅ File ingestion with streaming uploads and validation
- ✅ Text extraction from multiple document formats
- ✅ Sentence-aware text chunking with overlap
- ✅ Generating embeddings with sentence-transformers
- ✅ Vector similarity search with PostgreSQL pgvector
- ✅ Background task processing pipeline
- ✅ Production project structure (config, models, schemas, crud, services, routers)
