# 06 — Metadata Filtering and Hybrid Search

## The Problem with Pure Vector Search

Vector search matches **meaning**, but sometimes you also need to match **facts**.

```
User query: "What does the 2024 annual report say about revenue?"

Pure vector search returns:
  ✅ Chunk from 2024 annual report (relevant!)
  ❌ Chunk from 2022 annual report (similar meaning, wrong year!)
  ❌ Chunk from a blog post about revenue (similar topic, wrong source!)
```

The fix: **metadata filtering** — restrict the search to specific document types,
date ranges, or users BEFORE computing vector similarity.

---

## Pre-Filter vs Post-Filter

### Pre-Filter (Recommended — do this)

```
Apply metadata filters FIRST → then vector search on the filtered subset.

1. WHERE document_type = 'annual_report' AND year = 2024
2. ORDER BY embedding <=> query_embedding
3. LIMIT 5
```

Faster because vector search runs on a smaller dataset.
PostgreSQL does this naturally with WHERE clauses.

### Post-Filter (Avoid when possible)

```
1. Vector search on ALL documents → get top 100
2. Filter those 100 by metadata → keep matches
3. Return top 5

Problem: if only 2 of the top 100 match the metadata filter,
you get 2 results instead of 5.
```

### pgvector Pre-Filtering (SQL)

```sql
-- Pre-filter by document type AND owner, then vector search
SELECT
    c.id,
    c.content,
    c.page_number,
    d.filename,
    1 - (c.embedding <=> $1) AS similarity
FROM document_chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.owner_id = $2                              -- tenant isolation
  AND d.content_type = 'application/pdf'           -- PDFs only
  AND d.created_at > '2024-01-01'                  -- recent docs only
  AND 1 - (c.embedding <=> $1) > 0.3              -- minimum similarity
ORDER BY c.embedding <=> $1
LIMIT 5;
```

---

## Filterable Metadata Fields

Design your metadata to answer the questions users will filter by:

| Field | Type | Filter Example |
|-------|------|---------------|
| `owner_id` | UUID | Always (tenant isolation) |
| `document_name` | String | "Search only in report.pdf" |
| `content_type` | String | "Only PDFs" or "Only DOCX" |
| `page_number` | Integer | "Only first 10 pages" |
| `created_at` | Timestamp | "Uploaded this month" |
| `document_status` | String | "Only indexed documents" (skip processing ones) |
| `heading` | String | "Only sections about 'Authentication'" |
| `tag` | String[] | User-defined tags like "legal", "finance" |
| `file_size` | Integer | Exclude very small/large documents |

### In SQLAlchemy:

```python
# Add useful metadata columns to your Document model
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, default=uuid4)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(String(20), default="uploaded")
    owner_id = Column(UUID, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # User-defined tags for filtering
    tags = Column(ARRAY(String), default=[])  # PostgreSQL ARRAY type

# Filter by tags:
query = select(Document).where(Document.tags.contains(["finance"]))
```

---

## Hybrid Search: Vector + Full-Text (Best of Both Worlds)

**Vector search** is great for: semantic matching, conceptual questions, paraphrasing.
**Full-text search** is great for: exact terms, names, codes, specific phrases.

**Hybrid search** combines both to get higher quality results than either alone.

### Approach 1: PostgreSQL ts_vector + pgvector

```sql
-- Add a tsvector column for full-text search
ALTER TABLE document_chunks ADD COLUMN search_vector TSVECTOR;

-- Populate it (run on insert/update)
UPDATE document_chunks
SET search_vector = to_tsvector('english', content);

-- Create a GIN index for fast full-text search
CREATE INDEX idx_chunks_fts ON document_chunks USING gin(search_vector);

-- HYBRID QUERY: combine full-text rank + vector similarity
WITH vector_results AS (
    SELECT id, content, page_number, document_id,
           1 - (embedding <=> $1) AS vector_score
    FROM document_chunks
    WHERE 1 - (embedding <=> $1) > 0.3
    ORDER BY embedding <=> $1
    LIMIT 20
),
text_results AS (
    SELECT id, content, page_number, document_id,
           ts_rank(search_vector, plainto_tsquery('english', $2)) AS text_score
    FROM document_chunks
    WHERE search_vector @@ plainto_tsquery('english', $2)
    ORDER BY text_score DESC
    LIMIT 20
)
-- Reciprocal Rank Fusion: combine scores from both methods
SELECT
    COALESCE(v.id, t.id) AS id,
    COALESCE(v.content, t.content) AS content,
    COALESCE(v.vector_score, 0) AS vector_score,
    COALESCE(t.text_score, 0) AS text_score,
    -- RRF formula: 1/(k + rank)
    (1.0 / (60 + COALESCE(v_rank, 999))) +
    (1.0 / (60 + COALESCE(t_rank, 999))) AS rrf_score
FROM vector_results v
FULL OUTER JOIN text_results t ON v.id = t.id
ORDER BY rrf_score DESC
LIMIT 5;
```

### Approach 2: Reciprocal Rank Fusion (RRF) in Python

RRF is simpler to implement in Python and doesn't require complex SQL:

```python
def reciprocal_rank_fusion(
    vector_results: list[tuple[str, float]],  # [(chunk_id, score), ...]
    text_results: list[tuple[str, float]],
    k: int = 60,  # RRF constant (default 60 is standard)
) -> list[tuple[str, float]]:
    """
    Combines vector and text search results using RRF.

    RRF score = Σ (1 / (k + rank_i)) across all result lists

    Higher k gives more weight to all results.
    Lower k gives more weight to top-ranked results.
    """
    rrf_scores: dict[str, float] = {}

    # Score from vector results
    for rank, (chunk_id, _) in enumerate(vector_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank)

    # Score from text results
    for rank, (chunk_id, _) in enumerate(text_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank)

    # Sort by combined score (descending)
    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
```

---

## When to Use What

```
User says: "authentication"
  → Full-text search works great (exact keyword)
  → Vector search also works (matches meaning)
  → Hybrid is best (finds both exact and semantic matches)

User says: "How do I keep users logged in?"
  → Full-text search fails (no match for "authentication" or "JWT")
  → Vector search succeeds (semantic match to auth concepts)
  → Use vector search

User says: "RFC 7519"
  → Full-text search succeeds (exact code)
  → Vector search may fail (doesn't know what RFC 7519 is)
  → Use full-text search

User says: "error code TASK_NOT_FOUND"
  → Full-text search succeeds (exact term)
  → Vector search may work (but less precisely)
  → Use full-text search
```

### Decision Matrix

| Query Type | Best Approach |
|-----------|---------------|
| Conceptual question | Vector search |
| Exact term / code | Full-text search |
| Named entity (person, product) | Full-text search |
| Paraphrased question | Vector search |
| Mixed (concept + specific term) | Hybrid search |

---

## Advanced: Qdrant Hybrid Search

Qdrant has built-in hybrid search (dense + sparse vectors):

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

# Hybrid search with dense (embedding) + sparse (BM25) vectors
results = client.query_points(
    collection_name="documents",
    prefetch=[
        # Dense vector search
        models.Prefetch(
            query=dense_embedding,
            using="dense",
            limit=20,
        ),
        # Sparse vector search (BM25-like)
        models.Prefetch(
            query=sparse_vector,
            using="sparse",
            limit=20,
        ),
    ],
    # Reciprocal Rank Fusion
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=5,
)
```

---

## Search API Design Patterns

### Basic Search Endpoint

```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # Metadata filters (all optional)
    document_ids: Optional[list[str]] = None   # specific documents
    content_types: Optional[list[str]] = None  # ["application/pdf"]
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[list[str]] = None

    # Search mode
    mode: Literal["semantic", "keyword", "hybrid"] = "semantic"

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    document_name: str
    page_number: Optional[int]
    similarity_score: float
    highlight: Optional[str] = None  # snippet with query terms bolded
```

### Response with Citations

```python
class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total_found: int
    search_mode: str
    search_time_ms: float
    # Citations for the UI:
    # "Based on: guide.pdf (p.3), report.pdf (p.12)"
    sources_summary: str
```
