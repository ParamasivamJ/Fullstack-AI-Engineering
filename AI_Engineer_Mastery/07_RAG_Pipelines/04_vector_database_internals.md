# Vector Database Internals — ANN, HNSW, IVF

## Beyond Product Names

Pinecone, Weaviate, Qdrant, Milvus, pgvector, Chroma — these are products. This guide covers the **internals** so you understand the engineering behind them.

---

## The Fundamental Problem

You have 1 million vectors (1M document chunks, each 384 dimensions). A user query becomes a vector. You need to find the 5 most similar vectors. Brute force = 1M cosine similarity calculations per query. At 384 dimensions: ~50ms. Sounds okay — until you have 100M vectors or 1000 queries/second.

---

## Approximate Nearest Neighbor (ANN)

ANN trades a small amount of accuracy for massive speed gains:

```
EXACT search:   100% recall,  50ms for 1M vectors
HNSW (ANN):      95% recall,   1ms for 1M vectors  ← 50x faster!
IVFFlat (ANN):   90% recall,   5ms for 1M vectors  ← 10x faster
```

"95% recall" means: of the true top-5 results, HNSW returns 4-5 of them. The one it misses is usually #5 or #6 anyway.

---

## HNSW (Hierarchical Navigable Small World)

### How It Works

Build a multi-layer graph where each layer is progressively sparser:

```
Layer 3 (sparse):    A ─────────── D
                     
Layer 2 (medium):    A ──── C ──── D ──── F
                     
Layer 1 (dense):     A ─ B ─ C ─ D ─ E ─ F ─ G ─ H

SEARCH:
  Start at top layer (few nodes, big jumps)
  → Find approximate region
  Drop to next layer (more nodes, smaller jumps)
  → Refine position
  Drop to bottom layer (all nodes)
  → Find exact nearest neighbors
  
  Like using a world map → country map → city map → street map
```

### Key Parameters

| Parameter | What It Controls | Typical Value |
|-----------|-----------------|---------------|
| `m` | Max connections per node | 16-64 |
| `ef_construction` | Build-time search breadth (higher = better graph, slower build) | 64-200 |
| `ef_search` | Query-time search breadth (higher = better recall, slower query) | 50-200 |

### Tradeoffs

- **Build time**: O(n × log n) — building the graph is slow
- **Memory**: O(n × m) — stores the graph in RAM
- **Query time**: O(log n) — very fast at query time
- **Updates**: Adding new vectors is easy. Deleting is expensive.

---

## IVF (Inverted File Index)

### How It Works

Divide vector space into clusters. Only search relevant clusters.

```
INDEXING:
  1. Run K-means clustering on all vectors → create 100 clusters
  2. Assign each vector to its nearest cluster centroid
  3. Store vectors grouped by cluster

SEARCHING:
  1. Compare query to 100 cluster centroids (fast)
  2. Pick top 5 closest clusters (nprobe=5)
  3. Brute-force search within those 5 clusters only
  
  Search 5% of data instead of 100% → 20x speedup

PARAMETERS:
  nlist:  number of clusters (typically √n or 4×√n)
  nprobe: clusters to search at query time (tradeoff: speed vs recall)
```

### IVF-PQ (Product Quantization)

Compress vectors to use less memory:

```
Original: 384 × float32 = 1536 bytes per vector
With PQ:  96 × uint8 = 96 bytes per vector → 16x compression!

1M vectors: 1.5GB → 96MB
Recall drops ~5% but memory savings are massive.
```

---

## pgvector (PostgreSQL Extension)

### Why pgvector?

- **Simplicity**: Same database for structured data AND vectors
- **ACID**: Transactions, rollbacks, consistency
- **SQL**: Filter with WHERE clauses + vector search in one query
- **No extra infrastructure**: No separate vector DB to manage

### Index Types

```sql
-- HNSW (recommended for most cases)
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- IVFFlat (good for very large datasets)
CREATE INDEX ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### When to Use pgvector vs Dedicated Vector DB

| Factor | pgvector | Qdrant/Pinecone/Weaviate |
|--------|----------|--------------------------|
| Vectors < 5M | ✅ Great | Overkill |
| Vectors > 10M | ⚠️ Possible | ✅ Built for this |
| Need SQL joins | ✅ Native | ❌ Separate query |
| Multi-tenancy | ✅ WHERE owner_id = | ✅ Namespace/collection |
| Ops complexity | ✅ Just PostgreSQL | ❌ Extra service |
| Filtering | ✅ Full SQL | ✅ Metadata filters |
| Real-time updates | ✅ INSERT/DELETE | ⚠️ Varies by product |

### Filtering Support (Pre vs Post)

When users query "Find policies about refunds where department=HR":

- **Pre-filtering**: Filter for "department=HR" first, then vector search the remaining subset. (Accurate, but slow if subset is large).
- **Post-filtering**: Vector search first to get top 100, then filter out non-HR results. (Fast, but might return 0 results if the top 100 don't match the filter!).
- **Single-stage (Native)**: Modern vector DBs (Qdrant, pgvector) merge filtering into the graph traversal itself, checking metadata at each node. Best of both worlds.

### Sharding & Persistence

- **Sharding**: Splitting the vector index across multiple machines. Critical when index size exceeds RAM (100M+ vectors). 
- **Persistence**: Vector indexes (like HNSW) live in RAM for speed. Persistence mechanisms (write-ahead logs, disk snapshots) ensure the index isn't lost on restart. Some databases use memory-mapped files (mmap) to keep the index on SSD but access it like RAM (slightly slower, much cheaper).

---

## Operations: Upsert, Delete, Compaction

```
UPSERT: Insert or update a vector by ID
  INSERT INTO chunks (id, embedding, content) VALUES (...)
  ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding;

DELETE: Remove vectors
  DELETE FROM chunks WHERE document_id = 'abc';
  ⚠️ HNSW: deleted nodes leave "holes" in the graph
  → Periodic REINDEX to rebuild the graph cleanly

COMPACTION: Reclaim space after many deletes
  REINDEX INDEX ix_chunks_embedding_hnsw;
  Schedule this during low-traffic periods.

CONSISTENCY:
  pgvector: fully consistent (ACID)
  Qdrant: eventually consistent (updates visible after refresh)
  Pinecone: eventually consistent (~seconds delay)
```

---

## How Vector DBs Fit with SQL and Object Storage

```
┌─────────────────────────────────────────────────┐
│  PostgreSQL (pgvector)                           │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ documents    │  │ document_chunks           │  │
│  │ (metadata)   │  │ (text + embedding vector)│  │
│  │ id, name,    │  │ id, doc_id, content,     │  │
│  │ status,      │  │ embedding VECTOR(384),   │  │
│  │ owner_id     │  │ page_number, chunk_index │  │
│  └──────┬───────┘  └──────────────────────────┘  │
│         │ FK                                      │
└─────────┼────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────┐
│  Object Storage (S3 / local disk)                 │
│  Original files: uploads/{uuid}.pdf               │
│  Never store large files in PostgreSQL.            │
└──────────────────────────────────────────────────┘

QUERY FLOW:
  1. User searches → embed query → cosine search in pgvector
  2. Get matching chunks with document_id
  3. JOIN with documents table for filename, owner
  4. Return results with citations
```
