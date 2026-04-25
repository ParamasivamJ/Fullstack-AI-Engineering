# 03 — Chunking Strategies (The Most Underrated Skill in RAG)

## Why Chunking Matters More Than Your LLM Choice

Your RAG pipeline is only as good as its chunks.

If chunks are too large → irrelevant text dilutes the useful content, the LLM
gets confused, and your answer quality drops.

If chunks are too small → context is lost, the LLM gets fragments without
meaning, and answers are shallow or wrong.

If chunks break mid-sentence → embeddings are garbage because the vector
represents a broken thought.

**Chunking is the most impactful optimization point in any RAG pipeline.**

---

## The 6 Chunking Strategies (Simple to Advanced)

### Strategy 1: Fixed-Size Character Chunking

```
Split text every N characters, with M characters of overlap.
```

```python
def fixed_size_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Simplest strategy. Fast but dumb.
    Breaks mid-word, mid-sentence — produces low-quality embeddings.
    Use only for prototyping, never in production.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # overlap with previous chunk
    return chunks
```

| Pros | Cons |
|------|------|
| Dead simple | Breaks mid-sentence and mid-word |
| Predictable chunk sizes | Embedding quality is poor |
| Fast | No semantic awareness |

---

### Strategy 2: Sentence-Aware Chunking ⭐ (Recommended for this project)

```
Split on sentence boundaries. Group sentences until chunk_size is reached.
Never break mid-sentence.
```

```python
import re

def sentence_aware_chunks(
    text: str,
    max_chunk_size: int = 512,
    overlap_sentences: int = 2,
) -> list[str]:
    """
    Splits text at sentence boundaries, groups into chunks.
    Each chunk is a coherent set of sentences.
    Overlap is measured in sentences (not characters) — semantically cleaner.
    """
    # Split into sentences (handles Mr., Dr., etc. reasonably well)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk_sentences = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)

        if current_size + sentence_size > max_chunk_size and current_chunk_sentences:
            # Save current chunk
            chunks.append(" ".join(current_chunk_sentences))

            # Overlap: keep last N sentences for context continuity
            current_chunk_sentences = current_chunk_sentences[-overlap_sentences:]
            current_size = sum(len(s) for s in current_chunk_sentences)

        current_chunk_sentences.append(sentence)
        current_size += sentence_size

    # Don't forget the last chunk
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    return chunks
```

| Pros | Cons |
|------|------|
| Never breaks mid-sentence | Chunk sizes vary |
| Better embedding quality | Slightly more complex |
| Semantic overlap | Long sentences can exceed chunk_size |

---

### Strategy 3: Recursive Character Splitting (LangChain default)

```
Try to split on "\n\n" first (paragraphs).
If chunks are still too big, split on "\n" (lines).
If still too big, split on ". " (sentences).
If still too big, split on " " (words).
```

```python
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

def recursive_split(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separators: list[str] = None,
) -> list[str]:
    """
    LangChain's RecursiveCharacterTextSplitter logic.
    Tries to split at the most semantically meaningful boundary first.
    Falls back to less meaningful boundaries for oversized chunks.
    """
    if separators is None:
        separators = SEPARATORS

    separator = separators[0]
    remaining_separators = separators[1:]

    # Split by the current separator
    splits = text.split(separator) if separator else list(text)

    chunks = []
    current_chunk = ""

    for split in splits:
        candidate = current_chunk + separator + split if current_chunk else split

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If this single split is bigger than chunk_size, recurse with next separator
            if len(split) > chunk_size and remaining_separators:
                sub_chunks = recursive_split(split, chunk_size, overlap, remaining_separators)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = split

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c]
```

| Pros | Cons |
|------|------|
| Preserves natural boundaries | More complex logic |
| Industry standard (LangChain uses this) | Overlap handling is tricky |
| Adapts to document structure | |

---

### Strategy 4: Semantic Chunking (Advanced)

```
Split text where the MEANING changes (topic shift).
Uses embeddings to detect semantic boundaries.
```

```python
# Concept — requires sentence-transformers

def semantic_chunks(text: str, threshold: float = 0.5) -> list[str]:
    """
    1. Split text into sentences
    2. Embed each sentence
    3. Compute cosine similarity between consecutive sentences
    4. Where similarity drops below threshold → chunk boundary

    This is the highest-quality chunking strategy but also the most expensive.
    You are generating embeddings TWICE: once for chunking, once for indexing.
    """
    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")

    sentences = text.split(". ")
    if len(sentences) < 2:
        return [text]

    embeddings = model.encode(sentences)

    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        # Cosine similarity between consecutive sentences
        sim = np.dot(embeddings[i], embeddings[i-1]) / (
            np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i-1])
        )

        if sim < threshold:
            # Topic shift detected — start new chunk
            chunks.append(". ".join(current_chunk) + ".")
            current_chunk = [sentences[i]]
        else:
            current_chunk.append(sentences[i])

    if current_chunk:
        chunks.append(". ".join(current_chunk) + ".")

    return chunks
```

| Pros | Cons |
|------|------|
| Highest quality chunks | 2x embedding cost |
| Topic-aware boundaries | Slow on large documents |
| Adapts to content | Threshold tuning required |

---

### Strategy 5: Document-Structure-Aware Chunking

```
Use the document's own structure (headings, sections) as chunk boundaries.
Each "section" is one chunk. Sub-sections become sub-chunks.
```

```python
def structure_aware_chunks(paragraphs: list[dict]) -> list[dict]:
    """
    Uses document headings (from python-docx extraction) to create chunks.
    Each section = one chunk with its heading as metadata.

    Input: list of {"text": "...", "style": "Heading 1" | "Normal", ...}
    Output: list of {"heading": "...", "content": "...", "level": 1}
    """
    chunks = []
    current_heading = "Introduction"
    current_content = []
    current_level = 0

    for para in paragraphs:
        if para.get("is_heading"):
            # Save previous section as a chunk
            if current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": " ".join(current_content),
                    "level": current_level,
                })
            # Start new section
            current_heading = para["text"]
            current_level = int(para["style"][-1]) if para["style"][-1].isdigit() else 0
            current_content = []
        else:
            current_content.append(para["text"])

    # Don't forget the last section
    if current_content:
        chunks.append({
            "heading": current_heading,
            "content": " ".join(current_content),
            "level": current_level,
        })

    return chunks
```

---

### Strategy 6: Parent-Child Chunking (Agentic RAG)

```
Create TWO levels of chunks:
  - Parent chunks: large (2000 chars) — returned to the LLM for full context
  - Child chunks: small (200 chars) — used for embedding and retrieval

Search finds the child → returns the parent.
This gives the LLM more context while keeping search precise.
```

```
Parent Chunk (2000 chars):
┌─────────────────────────────────────────────────────────────┐
│  "FastAPI is a modern web framework for building APIs with  │
│  Python 3.6+ based on standard Python type hints. It is    │
│  one of the fastest Python frameworks available..."         │
│                                                             │
│  Child 1 (200):     Child 2 (200):     Child 3 (200):       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ "FastAPI is  │   │ "It is one  │   │ "The key    │       │
│  │  a modern..."│   │  of the..."  │   │  features..."│     │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │               │
│    Embedding A       Embedding B       Embedding C          │
└─────────────────────────────────────────────────────────────┘

Search query: "What framework is fast?"
  → Matches Child 2 (high similarity to "one of the fastest")
  → Returns Parent Chunk (full 2000 chars of context)
```

---

## Overlap: Why and How Much

```
Without overlap:
  Chunk 1: "FastAPI uses Pydantic for data validation."
  Chunk 2: "This means all input is automatically validated."
  
  Problem: If someone asks "How does FastAPI validate input?",
  the answer spans two chunks but neither chunk alone answers it.

With 2-sentence overlap:
  Chunk 1: "FastAPI uses Pydantic for data validation. This means all input is automatically validated."
  Chunk 2: "This means all input is automatically validated. You define schemas with type hints..."
  
  Now both chunks contain the bridge sentence.
```

### Overlap Guidelines

| Document Type | Recommended Overlap |
|--------------|-------------------|
| Technical docs | 10–20% of chunk size |
| Legal contracts | 20–30% (precision critical) |
| Chat logs | 0–5% (short, self-contained turns) |
| Academic papers | 15–20% |

---

## Chunk Size: The Numbers That Matter

| Chunk Size | Best For | Embedding Model |
|-----------|---------|-----------------|
| 100–200 chars | Precise retrieval (FAQ answers) | all-MiniLM-L6-v2 |
| 300–500 chars | General RAG (balanced) | all-MiniLM-L6-v2 |
| 500–1000 chars | Long-form context (reports) | text-embedding-3-small |
| 1000–2000 chars | Parent chunks in parent-child strategy | any |

**Rule of thumb:** Match chunk size to the expected answer length.
If the answer is one sentence, use small chunks.
If the answer needs a full paragraph, use larger chunks.

---

## LangChain Chunking (Ready-Made)

```python
# pip install langchain-text-splitters

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
    SentenceTransformersTokenTextSplitter,
)

# Standard recursive splitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
)
chunks = splitter.split_text(document_text)

# Token-based splitter (for exact token count control)
token_splitter = TokenTextSplitter(
    chunk_size=256,   # in tokens, not characters
    chunk_overlap=20,
)

# Sentence-transformers-aware splitter
st_splitter = SentenceTransformersTokenTextSplitter(
    chunk_overlap=50,
    model_name="all-MiniLM-L6-v2",
)
```

---

## Metadata: What to Attach to Each Chunk

Every chunk should carry metadata for filtering and citation:

```python
chunk = {
    "content": "The actual text...",
    "metadata": {
        "document_id": "uuid-of-document",
        "document_name": "fastapi_guide.pdf",
        "page_number": 3,
        "chunk_index": 7,             # position in document
        "heading": "Dependency Injection",  # nearest heading
        "content_type": "application/pdf",
        "total_chunks": 42,
        "char_count": 487,
        "created_at": "2026-04-25T10:00:00Z",
        "owner_id": "user_123",       # for tenant isolation
    }
}
```

This metadata powers:
- **Citations**: "Based on fastapi_guide.pdf, page 3"
- **Filtering**: "Search only in PDFs uploaded this week"
- **Ordering**: Reconstruct original document order from chunk_index
- **Security**: Only search within the current user's documents
