# 04 — Embeddings Explained (From Zero to Expert)

## What Is an Embedding?

An embedding is a list of numbers (a vector) that represents the MEANING of text.

```
"FastAPI is a web framework"  →  [0.12, -0.45, 0.78, 0.03, ..., -0.21]
                                  ↑ 384 numbers for all-MiniLM-L6-v2
                                  ↑ 1536 numbers for OpenAI text-embedding-3-small
```

Two pieces of text with similar meaning will have similar vectors.
Two pieces of text with different meanings will have different vectors.

This is the foundation of semantic search: instead of matching keywords,
you match meaning.

---

## How Embeddings Are Created

```
                     Embedding Model
Input Text   ─────►  (Neural Network)  ─────►  Vector
"What is AI?"         Transformer            [0.12, -0.45, ...]
                      Architecture
                      (BERT-based)
```

The model was trained on billions of text pairs to learn that:
- "dog" and "puppy" should have similar vectors
- "dog" and "skyscraper" should have very different vectors
- "What is the capital of France?" and "Paris is the capital" should be close

You don't train the model. You download a pre-trained one and use it.

---

## Key Properties of Embedding Vectors

### 1. Dimensionality
The number of values in the vector. More dimensions = more nuance, but more storage and computation.

| Model | Dimensions | Quality | Speed |
|-------|-----------|---------|-------|
| all-MiniLM-L6-v2 | 384 | Good | ⚡ Very fast |
| all-mpnet-base-v2 | 768 | Better | 🔄 Medium |
| text-embedding-3-small (OpenAI) | 1536 | Very good | ☁️ API call |
| text-embedding-3-large (OpenAI) | 3072 | Excellent | ☁️ API call |
| bge-large-en-v1.5 | 1024 | Excellent | 🐢 Slower |
| nomic-embed-text | 768 | Very good | ⚡ Fast |

### 2. Normalization
Most embedding models output **normalized vectors** (unit length = 1.0).
This means cosine similarity = dot product (saves computation).

```python
import numpy as np

vec = model.encode("hello world")
# Check if normalized:
length = np.linalg.norm(vec)
print(length)  # Should be ~1.0 for normalized models
```

### 3. Max Sequence Length
Every model has a maximum input length. Text beyond this is **silently truncated**.

| Model | Max Tokens | ~Max Characters |
|-------|-----------|-----------------|
| all-MiniLM-L6-v2 | 256 | ~1024 |
| all-mpnet-base-v2 | 384 | ~1536 |
| text-embedding-3-small | 8191 | ~32,000 |
| bge-large-en-v1.5 | 512 | ~2048 |

**This is why chunk size must match your embedding model's max length.**
If your chunks are 2000 characters but your model truncates at 1024, you lose
half the content silently — and your search quality suffers.

---

## Using sentence-transformers (Local, Free)

```python
# pip install sentence-transformers

from sentence_transformers import SentenceTransformer
import numpy as np

# Load model (downloads ~90MB on first run, then cached)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Single text → single vector
embedding = model.encode("FastAPI is a modern Python web framework")
print(type(embedding))    # numpy.ndarray
print(embedding.shape)    # (384,)
print(embedding[:5])      # [0.123, -0.456, ...]

# Batch encoding (much faster than one-by-one)
texts = [
    "FastAPI is built on Starlette and Pydantic",
    "Django is a batteries-included web framework",
    "Quantum computing uses qubits instead of bits",
]
embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)
print(embeddings.shape)  # (3, 384)

# Compute similarities between all pairs
from sentence_transformers import util
similarities = util.cos_sim(embeddings, embeddings)
print(similarities)
# [[1.0, 0.6, 0.1],    FastAPI-FastAPI, FastAPI-Django, FastAPI-Quantum
#  [0.6, 1.0, 0.08],   Django-FastAPI,  Django-Django,  Django-Quantum
#  [0.1, 0.08, 1.0]]   Quantum-FastAPI, Quantum-Django, Quantum-Quantum
```

---

## Using OpenAI Embeddings (Cloud API, Paid)

```python
# pip install openai

from openai import OpenAI

client = OpenAI(api_key="sk-...")

def get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Returns a 1536-dimensional vector.
    Cost: ~$0.02 per 1 million tokens.
    """
    response = client.embeddings.create(
        input=text,
        model=model,
    )
    return response.data[0].embedding

# For batches (up to 2048 texts at once):
def get_openai_embeddings_batch(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [item.embedding for item in response.data]
```

---

## Using Hugging Face Transformers (More Control)

```python
# pip install transformers torch

from transformers import AutoTokenizer, AutoModel
import torch

def get_hf_embedding(text: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    # Tokenize
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256, padding=True)

    # Forward pass (no gradient computation needed for inference)
    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling: average all token embeddings into one vector
    # (CLS token alone is less accurate for sentence similarity)
    attention_mask = inputs["attention_mask"]
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embedding = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )

    # Normalize to unit length
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

    return embedding.squeeze().numpy().tolist()
```

---

## Similarity Metrics: How to Compare Vectors

### Cosine Similarity (most common for text embeddings)

```
cosine_similarity(A, B) = dot(A, B) / (||A|| * ||B||)

Range: -1 to 1
  1.0 = identical direction (same meaning)
  0.0 = perpendicular (unrelated)
 -1.0 = opposite (antonym — rare in practice)
```

### Cosine Distance (used in pgvector's <=> operator)

```
cosine_distance = 1 - cosine_similarity

Range: 0 to 2
  0.0 = identical (most similar)
  1.0 = perpendicular
  2.0 = opposite

pgvector sorts by <=> ascending, so LOWER = MORE SIMILAR
```

### Euclidean Distance (L2)

```
L2_distance(A, B) = sqrt(sum((a_i - b_i)^2))

Range: 0 to ∞
  0.0 = identical
  Higher = less similar

Better for non-normalized vectors. Used in some image search systems.
```

### Dot Product (Inner Product)

```
dot_product(A, B) = sum(a_i * b_i)

For normalized vectors: dot_product = cosine_similarity
Faster to compute (no division).
Use when vectors are already normalized (most sentence-transformer models are).
```

### Which to Use?

| Metric | When | pgvector Operator |
|--------|------|------------------|
| **Cosine distance** | Text embeddings (almost always) | `<=>` |
| **L2 (Euclidean)** | Image embeddings, non-normalized vectors | `<->` |
| **Inner product** | Normalized text embeddings (faster) | `<#>` |

---

## Embedding Model Selection Guide

| Your Scenario | Model | Why |
|--------------|-------|-----|
| **Learning / prototyping** | all-MiniLM-L6-v2 | Free, fast, good enough |
| **Production (budget)** | all-MiniLM-L6-v2 or nomic-embed-text | Free, local, no API costs |
| **Production (quality)** | text-embedding-3-small (OpenAI) | Best quality per dollar |
| **Multi-language** | paraphrase-multilingual-MiniLM-L12-v2 | 50+ languages |
| **Maximum accuracy** | text-embedding-3-large (OpenAI) or bge-large | Best benchmarks |
| **Code search** | code-search-ada-code-001 or Voyage Code | Trained on code |
| **On-premise (no cloud)** | all-MiniLM-L6-v2 or bge-base | Runs fully local |

---

## Performance: Embedding Speed

```python
# Benchmark: Embedding 1000 text chunks of ~500 chars each

model = SentenceTransformer("all-MiniLM-L6-v2")

import time
texts = ["Sample text chunk " * 30] * 1000  # 1000 chunks

start = time.perf_counter()
embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)
elapsed = time.perf_counter() - start

print(f"1000 chunks in {elapsed:.2f}s")
# CPU: ~3-5 seconds
# GPU: ~0.3-0.5 seconds

# OpenAI API:
# 1000 chunks ≈ 2-3 seconds (network latency + processing)
# Cost: ~$0.0001 (basically free)
```

### Optimization Tips

1. **Batch encoding** — encode all chunks at once, not one-by-one
2. **GPU acceleration** — `model = SentenceTransformer("...", device="cuda")`
3. **Caching** — don't re-embed unchanged documents
4. **Async** — for OpenAI API, use `asyncio.gather()` to embed in parallel
5. **Quantization** — use `float16` instead of `float32` to halve storage

---

## Common Mistakes

### ❌ Using the wrong model for search

```
# Query: "How does authentication work?"
# Document chunk: "JWT tokens provide stateless auth"

# If you use different models for query and document:
query_embedding = model_A.encode(query)      # 384-dim
doc_embedding = model_B.encode(document)     # 768-dim
# These vectors are INCOMPATIBLE — you can't compare them
```

**Rule: Always use the SAME model for queries and documents.**

### ❌ Not matching chunk size to model max length

```
# Model: all-MiniLM-L6-v2 (max 256 tokens ≈ 1024 chars)
# Chunk: 3000 characters
# Result: only the first 1024 chars are embedded, rest is silently lost
```

### ❌ Embedding raw extracted text (with artifacts)

```
# Raw PDF text: "Page 3 of 15\n\nFastAPI is a modern\nweb frame-\nwork for..."
# Clean text:   "FastAPI is a modern web framework for..."
# Always clean BEFORE embedding
```
