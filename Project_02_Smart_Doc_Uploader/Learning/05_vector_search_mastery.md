# 05 — Vector Search Mastery (pgvector + Qdrant)

## What Is Vector Search?

Traditional database search: `WHERE title LIKE '%fastapi%'` — matches **keywords**.
Vector search: `ORDER BY embedding <=> query_embedding` — matches **meaning**.

"How do I validate user input?" matches "Pydantic enforces type constraints"
even though they share zero keywords. That's the power of vector search.

---

## pgvector: Vector Search Inside PostgreSQL

pgvector adds a new column type (`vector`) and distance operators to PostgreSQL.
You keep your relational data and vector data in the SAME database.

### Setup

```sql
-- Enable the extension (run once)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table with a vector column
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding VECTOR(384),       -- 384 dimensions for all-MiniLM-L6-v2
    document_id UUID REFERENCES documents(id),
    page_number INT,
    chunk_index INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### The Three Distance Operators

```sql
-- COSINE DISTANCE (best for text embeddings)
-- Range: 0 (identical) to 2 (opposite)
SELECT *, embedding <=> '[0.1, 0.2, ...]' AS distance
FROM document_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 5;

-- L2 (EUCLIDEAN) DISTANCE (best for image embeddings)
SELECT *, embedding <-> '[0.1, 0.2, ...]' AS distance
FROM document_chunks
ORDER BY embedding <-> '[0.1, 0.2, ...]'
LIMIT 5;

-- INNER PRODUCT (fastest for normalized vectors)
-- Note: pgvector uses NEGATIVE inner product, so ORDER BY ASC
SELECT *, (embedding <#> '[0.1, 0.2, ...]') * -1 AS similarity
FROM document_chunks
ORDER BY embedding <#> '[0.1, 0.2, ...]'
LIMIT 5;
```

---

## Vector Indexes: HNSW vs IVFFlat

Without an index, pgvector does a **sequential scan** — it computes the distance
to EVERY row. This is accurate (exact) but slow for large tables.

Indexes enable **approximate nearest neighbor (ANN)** search — they sacrifice
a tiny bit of accuracy for massive speed gains.

### IVFFlat (Inverted File Index)

```sql
-- Create an IVFFlat index
CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
-- lists = sqrt(number of rows) is a good starting point
```

**How it works:**
1. Divides all vectors into `lists` clusters using k-means
2. On query: find the nearest clusters, then search only within those clusters
3. `probes` parameter controls how many clusters to search (more = slower but more accurate)

```sql
-- Set probes for a query (default is 1, too low for production)
SET ivfflat.probes = 10;

SELECT * FROM document_chunks
ORDER BY embedding <=> $1
LIMIT 5;
```

| Pros | Cons |
|------|------|
| Fast to build (minutes) | Need to rebuild after large inserts |
| Low memory usage | Lower recall than HNSW |
| Good for < 1M vectors | Requires tuning `lists` and `probes` |

### HNSW (Hierarchical Navigable Small Worlds) ⭐ Recommended

```sql
-- Create an HNSW index (takes longer to build but better quality)
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**How it works:**
1. Builds a multi-layer graph where each vector is a node
2. Higher layers have fewer nodes (long-distance navigation)
3. Lower layers have more nodes (precise local search)
4. Query navigates from top layer down to find nearest neighbors

**Parameters:**
- `m` (default 16): How many edges per node. Higher = better recall but more memory.
- `ef_construction` (default 64): How many candidates to consider during build. Higher = better index but slower build.

```sql
-- Set search quality for HNSW (at query time)
SET hnsw.ef_search = 100;  -- default is 40; higher = better recall, slower
```

| Pros | Cons |
|------|------|
| Higher recall (accuracy) | Slower to build (hours for large data) |
| No rebuild needed after inserts | Uses more memory |
| Better for production | Slightly slower inserts |

### When to Use Which?

| Scenario | Index | Why |
|----------|-------|-----|
| < 100K vectors | No index (exact scan) | Fast enough without it |
| 100K–1M vectors | HNSW | Best recall, handles inserts well |
| > 1M vectors | HNSW (or move to Qdrant) | pgvector gets slow beyond ~5M |
| Prototyping | No index or IVFFlat | Faster setup, good enough |
| Batch load, then search | IVFFlat | Fast index build |

---

## pgvector with SQLAlchemy (Python ORM)

```python
from sqlalchemy import Column, Text, Integer, select
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector  # pip install pgvector

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_number = Column(Integer)
    chunk_index = Column(Integer)


# SEARCH: Find similar chunks
async def search_similar(
    db: AsyncSession,
    query_embedding: list[float],
    top_k: int = 5,
    owner_id: str = None,
) -> list:
    """Semantic search with cosine distance."""

    # Cosine distance: lower = more similar
    cosine_distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - cosine_distance).label("similarity")

    query = (
        select(DocumentChunk, similarity)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.owner_id == owner_id)     # TENANT ISOLATION
        .where((1 - cosine_distance) > 0.3)       # minimum similarity threshold
        .order_by(cosine_distance)                  # ascending = most similar first
        .limit(top_k)
    )

    result = await db.execute(query)
    return [(row.DocumentChunk, float(row.similarity)) for row in result]
```

---

## Qdrant: The Alternative to pgvector

Qdrant is a purpose-built vector database. When pgvector is not enough.

### When to Use Qdrant Instead of pgvector

| Feature | pgvector | Qdrant |
|---------|----------|--------|
| **Vector count** | Good up to ~5M | Good up to billions |
| **Filter speed** | SQL WHERE (good but not optimized for vectors) | Payload filters (optimized) |
| **Setup** | Already part of PostgreSQL | Separate service (Docker) |
| **Memory** | Uses PostgreSQL's buffer | Dedicated vector memory |
| **Clustering** | No | Yes (distributed mode) |
| **Full-text search** | PostgreSQL's `tsvector` | Built-in BM25 |

### Qdrant Quick Start

```python
# pip install qdrant-client

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)

# Connect
client = QdrantClient(url="http://localhost:6333")

# Create collection (like a table)
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=384,                    # dimension of your embeddings
        distance=Distance.COSINE,    # similarity metric
    ),
)

# Insert vectors
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=[0.1, 0.2, ...],  # 384-dim embedding
            payload={                  # metadata (filterable)
                "document_name": "guide.pdf",
                "page_number": 3,
                "owner_id": "user_123",
                "content": "The actual text chunk...",
            },
        ),
    ],
)

# Search with filter
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, ...],  # query embedding
    limit=5,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="owner_id",
                match=MatchValue(value="user_123"),  # tenant isolation
            ),
        ],
    ),
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.payload['content']}")
```

---

## Search Quality Metrics

### Recall@K
"Of all the truly relevant chunks, how many did we find in the top K results?"

```
Relevant chunks in database: [A, B, C, D, E]  (5 total)
Top 5 search results:         [A, B, F, C, G]  (3 relevant found)

Recall@5 = 3/5 = 0.60 (60%)
```

### Precision@K
"Of the top K results, how many are actually relevant?"

```
Top 5 results: [A, B, F, C, G]
Relevant:      [A, B, C]        (3 out of 5 are relevant)

Precision@5 = 3/5 = 0.60 (60%)
```

### MRR (Mean Reciprocal Rank)
"How high is the first relevant result?"

```
Results: [F, G, A, B, C]   → first relevant (A) is at position 3
MRR = 1/3 = 0.33

Results: [A, F, B, G, C]   → first relevant (A) is at position 1
MRR = 1/1 = 1.00   ← perfect
```

---

## Performance Optimization Checklist

| Optimization | Impact | Effort |
|-------------|--------|--------|
| Add HNSW index | ⚡ 10–100x search speed | Low |
| Use batch embedding | ⚡ 5–10x embed speed | Low |
| Filter BEFORE vector search | ⚡ Reduces search space | Low |
| Use `float16` instead of `float32` | 📦 50% less storage | Medium |
| Cache frequent queries | ⚡ Instant for repeated queries | Medium |
| Partition by owner_id | ⚡ Faster per-user search | Medium |
| Move to Qdrant (>5M vectors) | ⚡ Purpose-built performance | High |

---

## Docker: Running pgvector Locally

```bash
# PostgreSQL with pgvector pre-installed
docker run -d \
  --name pgvector \
  -e POSTGRES_DB=docuploader \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppass \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Verify pgvector is available
docker exec -it pgvector psql -U appuser -d docuploader \
  -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

```bash
# Qdrant (alternative)
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  qdrant/qdrant
```
