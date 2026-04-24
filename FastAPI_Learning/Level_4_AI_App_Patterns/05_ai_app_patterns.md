# Level 4 — AI App Patterns: Concepts and Flow Diagrams

## The Big Picture: Why AI APIs Are Different

A traditional REST API does simple things:
1. Receive request → validate → query DB → return data.

An AI API does much more:
1. Receive request → validate → **embed query** → **search vector DB** → **build prompt** → **call LLM** → **stream response** → log tokens → update costs.

Each extra step adds latency, cost, and failure modes.
This level teaches you to design around all of them.

---

## The RAG Pipeline — Full Flow

```
User: "What is FastAPI's dependency injection?"
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Endpoint: POST /rag/query                          │
│                                                             │
│  1. VALIDATE                                                │
│     └── question length OK? model allowed? threshold valid? │
│                                                             │
│  2. EMBED QUERY                                             │
│     └── "What is FastAPI's dependency..." → [0.1, 0.4, ...]│
│         (384-dimensional vector)                            │
│                                                             │
│  3. VECTOR SEARCH (pgvector / Qdrant)                       │
│     └── SELECT chunks WHERE embedding <=> query_vec < 0.5  │
│         Returns: 3 most similar text chunks with scores     │
│                                                             │
│  4. BUILD PROMPT                                            │
│     └── "Given this context: [chunks]... Answer: [question]"│
│         The system prompt instructs the LLM to stay grounded│
│                                                             │
│  5. CHECK CACHE                                             │
│     └── Have we answered this exact question before?        │
│         YES → return cached answer (zero cost!)             │
│         NO  → continue                                      │
│                                                             │
│  6. CALL LLM (the expensive step)                           │
│     └── POST https://api.openai.com/v1/chat/completions     │
│         With timeout: 30 seconds                            │
│         With retry: 2 attempts on 429/503                   │
│                                                             │
│  7. STREAM RESPONSE                                          │
│     └── Send each token via SSE as it arrives               │
│         text/event-stream → browser updates in real-time    │
│                                                             │
│  8. LOG AND TRACK                                           │
│     └── Record: tokens used, cost, latency, user_id         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
User sees: Streamed answer with source citations
```

---

## Streaming: How SSE Works

```
Server                          Browser
  │                                │
  │  HTTP Response starts          │
  │  Content-Type: text/event-stream
  │ ─────────────────────────────► │
  │                                │  EventSource is open
  │  event: message                │
  │  data: {"token": "Based "}     │
  │ ─────────────────────────────► │  UI: "Based "
  │                                │
  │  event: message                │
  │  data: {"token": "on "}        │
  │ ─────────────────────────────► │  UI: "Based on "
  │                                │
  │  event: message                │
  │  data: {"token": "the "}       │
  │ ─────────────────────────────► │  UI: "Based on the "
  │                                │
  │  event: done                   │
  │  data: {}                      │
  │ ─────────────────────────────► │  EventSource.close()
  │                                │
  HTTP connection closes
```

---

## Cost Control Decision Tree

```
Request arrives
      │
      ▼
Is message > 4000 chars?  ──YES──► 422 Validation Error (reject early)
      │ NO
      ▼
Is this user over their quota? ──YES──► 429 Too Many Requests
      │ NO
      ▼
Is exact question in cache? ──YES──► Return cached answer (FREE)
      │ NO
      ▼
Route to cheapest capable model:
  Short question → gpt-4o-mini ($0.00015/1k)
  Complex task   → gpt-4o     ($0.0025/1k)
  Free tier      → gpt-4o-mini only
      │
      ▼
Set max_tokens limit
  (caps both output length and cost)
      │
      ▼
Call LLM with timeout=30s
      │
      ▼
Log tokens used → update user's monthly usage counter
      │
      ▼
Cache result → return response
```

---

## Document Ingestion Pipeline

```
User uploads PDF
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  POST /documents/ingest                                     │
│                                                             │
│  1. VALIDATE                                                │
│     ├── File type: PDF/DOCX/TXT only                        │
│     └── File size: < 10MB                                   │
│                                                             │
│  2. SAVE FILE                                               │
│     └── Upload to S3/GCS or local disk                      │
│                                                             │
│  3. RETURN "Accepted" IMMEDIATELY                           │
│     └── Don't make user wait for 10-second pipeline         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
      │
      │ Background task continues here
      ▼
┌─────────────────────────────────────────────────────────────┐
│  Background: index_document()                               │
│                                                             │
│  4. EXTRACT TEXT                                            │
│     └── PDF → text (using pdfplumber or PyMuPDF)            │
│                                                             │
│  5. CHUNK TEXT                                              │
│     └── Split into ~512 token chunks with 50-token overlap  │
│         Overlap prevents losing context at chunk boundaries │
│                                                             │
│  6. GENERATE EMBEDDINGS                                     │
│     └── For each chunk: model.encode(chunk_text)            │
│         Result: 384-dim vector per chunk                    │
│                                                             │
│  7. STORE IN VECTOR DB                                      │
│     └── INSERT INTO document_chunks (content, embedding, …) │
│         OR: qdrant_client.upsert(collection, points)        │
│                                                             │
│  8. UPDATE DOCUMENT STATUS → "indexed"                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
Document is now searchable!
```

---

## Files in This Level

| File | Core Concept |
|------|-------------|
| `01_chat_endpoint.py` | Non-streaming and streaming chat, multi-turn conversation |
| `03_rag_pipeline_template.py` | Full embed → retrieve → prompt → LLM pipeline |
| `06_token_and_cost_control.py` | Caching, model routing, token estimation, cost calculation |

Next: `Level_5_Professional_Engineering/` — make it secure, testable, and observable.
