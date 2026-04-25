# Embeddings — Vector Representations of Meaning

## The Core Intuition

An embedding is a **list of numbers** (a vector) that captures the **meaning** of a piece of text. Similar meanings → similar vectors. Different meanings → different vectors. This is the foundation of semantic search, RAG, recommendations, and clustering.

```
"king"    → [0.21, -0.45, 0.67, 0.12, ...]   (384 numbers)
"queen"   → [0.19, -0.43, 0.65, 0.14, ...]   (very similar!)
"bicycle" → [-0.56, 0.23, -0.11, 0.89, ...]  (very different)
```

The model has learned that "king" and "queen" are semantically related, so their vectors are close together in 384-dimensional space.

---

## How Embeddings Are Created

### Training Process

Embedding models are trained on billions of text pairs where the model learns:
- Sentences that mean the same thing → vectors should be close
- Sentences that mean different things → vectors should be far apart

```
TRAINING PAIR (positive):
  "How do I return an item?"  ↔  "What is your refund policy?"
  → Model learns these should have similar vectors

TRAINING PAIR (negative):
  "How do I return an item?"  ↔  "What's the weather today?"
  → Model learns these should have different vectors
```

### Popular Embedding Models

| Model | Dimensions | Max Tokens | Speed | Quality | Cost |
|-------|-----------|-----------|-------|---------|------|
| all-MiniLM-L6-v2 | 384 | 256 | ⚡ Fast | Good | Free (local) |
| text-embedding-3-small | 1536 | 8191 | Fast | Good | $0.02/1M tokens |
| text-embedding-3-large | 3072 | 8191 | Medium | Excellent | $0.13/1M tokens |
| BGE-large-en-v1.5 | 1024 | 512 | Medium | Excellent | Free (local) |
| Cohere embed-v3 | 1024 | 512 | Fast | Excellent | $0.10/1M tokens |
| Voyage-3 | 1024 | 32000 | Fast | Best | $0.06/1M tokens |
| GTE-Qwen2 | 768 | 8192 | Medium | Excellent | Free (local) |

---

## Similarity Metrics

### Cosine Similarity (Most Common)

Measures the **angle** between two vectors. Ignores magnitude, focuses on direction.

```
                    A · B           Σ(aᵢ × bᵢ)
cos(θ) = ─────────────────── = ─────────────────────
              ||A|| × ||B||     √Σ(aᵢ²) × √Σ(bᵢ²)

Range: -1 (opposite) to +1 (identical)
Typical threshold for "similar": > 0.7
```

**Why cosine over Euclidean?** Cosine is invariant to vector length. A short document and a long document about the same topic will have similar cosine similarity but very different Euclidean distances.

### Euclidean Distance (L2)

Measures the **straight-line distance** between two points in vector space.

```
L2(A, B) = √Σ(aᵢ - bᵢ)²

Range: 0 (identical) to ∞
Smaller = more similar (opposite of cosine!)
```

### Dot Product (Inner Product)

```
A · B = Σ(aᵢ × bᵢ)

When vectors are normalized (length = 1):
  dot product = cosine similarity
  
This is why most embedding models normalize their outputs.
```

### Which to Use?

| Metric | When to Use | pgvector Operator |
|--------|------------|-------------------|
| Cosine | Default choice. Works for any embedding model | `<=>` |
| L2 (Euclidean) | When magnitude matters (rare) | `<->` |
| Inner Product | When embeddings are already normalized | `<#>` |

---

## Vector Normalization

Most embedding models output **normalized vectors** (length = 1.0). This means:
- Cosine similarity = dot product (faster computation!)
- All vectors lie on the surface of a unit sphere
- You can use any similarity metric interchangeably

```python
import numpy as np

# Check if an embedding is normalized
embedding = model.encode("Hello world")
norm = np.linalg.norm(embedding)
print(f"Norm: {norm:.4f}")  # Should be ~1.0000

# Manually normalize if needed
normalized = embedding / np.linalg.norm(embedding)
```

---

## Embedding Drift

### The Problem

Over time, your embeddings become **stale**:
- You switch embedding models (v1 → v2) → old and new vectors are incompatible
- The model provider updates their model → existing embeddings subtly change
- Your domain vocabulary evolves → old embeddings don't capture new terms

### The Solution

```
DETECTION:
  Monitor average similarity scores over time.
  If search quality drops without query changes → likely drift.

PREVENTION:
  1. Pin your embedding model version (don't auto-update)
  2. Store the model name/version in metadata alongside each embedding
  3. When switching models: re-embed ALL existing documents
  4. Budget for periodic re-embedding (quarterly for most apps)

MIGRATION:
  Old model: all-MiniLM-L6-v2 (dim=384)
  New model: text-embedding-3-small (dim=1536)
  
  You CANNOT mix these! Must re-embed everything.
  Schedule: background job, 1000 docs/min, zero-downtime via dual-index.
```

---

## Choosing the Right Model

### Decision Framework

```
Need speed + free?
  → all-MiniLM-L6-v2 (384 dim, local, fastest)

Need quality + free?
  → BGE-large-en-v1.5 or GTE-Qwen2 (local, excellent quality)

Need simplicity + API?
  → OpenAI text-embedding-3-small (1536 dim, $0.02/1M tokens)

Need max quality + budget?
  → Cohere embed-v3 or Voyage-3 (best benchmarks, reasonable cost)

Need multilingual?
  → Cohere embed-v3 (100+ languages) or BGE-m3 (local)

Need long documents (>512 tokens)?
  → Voyage-3 (32K) or text-embedding-3-large (8K)
```

### Dimensions: More = Better?

Not always. Higher dimensions capture more nuance but:
- Use more storage (384 floats × 4 bytes = 1.5KB vs 3072 × 4 = 12KB per vector)
- Slower similarity computation
- Diminishing returns after ~768 for most RAG tasks

**Production tip**: OpenAI's text-embedding-3 models support dimension reduction. Request 512 dimensions instead of 1536 to save 67% storage with minimal quality loss.

---

## Production Patterns

### Batch Embedding

```python
# BAD: one at a time (slow, wasteful)
for text in texts:
    embedding = model.encode(text)  # 1 API call per text

# GOOD: batch encoding
embeddings = model.encode(texts, batch_size=64)  # 1 API call for 64 texts
# 10x faster, lower cost
```

### Caching Embeddings

```
RULE: Never embed the same text twice.

Strategy:
  1. Hash the text content (SHA-256)
  2. Check cache (Redis/DB) for existing embedding
  3. If found → return cached
  4. If not → compute, cache, return

  This saves 90%+ on embedding costs for apps with repeated queries.
```

### Embedding for Different Content Types

```
DOCUMENTS: Embed the full chunk text as-is.

QUERIES: Some models use different prefixes:
  - BGE: "Represent this sentence for retrieval: {query}"
  - E5: "query: {text}" for queries, "passage: {text}" for docs
  - OpenAI: No prefix needed (handles internally)
  
  Using the wrong prefix can drop retrieval quality by 10-20%!
```

---

## Real AI App Example

In a document search system:

```
INDEXING (once per document):
  PDF → extract text → chunk into 512-char segments
  → embed each chunk → store in pgvector/Qdrant/Pinecone

SEARCHING (every query):
  User query → embed query (same model!) → cosine search in vector DB
  → top-5 most similar chunks → send to LLM with user question
  → LLM generates answer grounded in retrieved chunks

CRITICAL RULE: The embedding model used for queries MUST be the
same model used for indexing. Mixing models = garbage results.
```

---

## Tradeoffs Summary

| Tradeoff | Small Model (384d) | Large Model (1536d+) |
|----------|-------------------|---------------------|
| Speed | ⚡ 5000 texts/sec | 🐌 500 texts/sec |
| Storage | 1.5 KB/vector | 6-12 KB/vector |
| Quality | Good (85-90% recall) | Excellent (92-97% recall) |
| Cost | Free (local) | $0.02-0.13/1M tokens |
| RAM | ~100MB model | ~2GB model |

**Start with the smallest model that meets your quality needs.** You can always upgrade later — just re-embed everything.
