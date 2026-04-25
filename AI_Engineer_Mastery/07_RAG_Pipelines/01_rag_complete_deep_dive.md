# RAG Pipeline — Complete Production Deep Dive

## What Is RAG?

Retrieval-Augmented Generation (RAG) is the pattern of **retrieving relevant documents** from your own data and **injecting them into the LLM's context** so it can answer with accurate, grounded, up-to-date information.

```
WITHOUT RAG:
  User: "What's our refund policy?"
  LLM:  "I don't have access to your policies." (or hallucinated answer)

WITH RAG:
  User: "What's our refund policy?"
  → Retriever finds: "Refund policy: 30-day full refund for all items..."
  → LLM sees the actual policy text
  LLM: "Your refund policy allows returns within 30 days for a full refund."
```

---

## The RAG Pipeline (End to End)

```
┌─────── INGESTION (runs once per document) ─────────────────────────────┐
│                                                                         │
│  Document → Parse → Clean → Chunk → Embed → Store in Vector DB         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────── RETRIEVAL + GENERATION (runs every query) ──────────────────────┐
│                                                                         │
│  Query → Embed → Search Vector DB → Rerank → Assemble Context → LLM   │
│                                             → Generate Answer           │
│                                             → Return with Citations     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Ingestion

### 1a. Document Parsing

| Format | Tool | Gotchas |
|--------|------|---------|
| PDF (text-based) | PyMuPDF, pdfplumber | Multi-column, headers/footers on every page |
| PDF (scanned) | Tesseract + pdf2image | OCR errors, handwriting |
| DOCX | python-docx | Embedded images not extracted |
| HTML | BeautifulSoup, trafilatura | Boilerplate removal (nav, footer) |
| Any format | Unstructured.io, Docling | Heavy but handles everything |

### 1b. Cleaning

```
CRITICAL ARTIFACTS TO REMOVE:
  ✗ Page headers/footers: "Confidential — Page 3 of 47"
  ✗ Broken hyphenation: "imple-\nmentation" → "implementation"
  ✗ Excessive whitespace: collapse triple newlines
  ✗ Boilerplate: copyright notices, disclaimers
  ✗ Encoding issues: "résumé" → "rÃ©sumÃ©"

PIPELINE:
  1. Fix encoding (chardet detection)
  2. Join hyphenated breaks: re.sub(r'(\w)-\n(\w)', r'\1\2', text)
  3. Remove page numbers: re.sub(r'^\s*Page \d+.*$', '', text)
  4. Collapse whitespace: re.sub(r'\n{3,}', '\n\n', text)
```

### 1c. Chunking

| Strategy | Quality | Best For |
|----------|---------|----------|
| Fixed-size (500 chars) | Low | Prototyping only |
| Sentence-aware | Good ⭐ | General RAG — never breaks mid-sentence |
| Recursive (LangChain) | Good | Mixed doc types |
| Semantic (embedding-based) | Excellent | Topic-shifting documents |
| Structure-aware | Excellent | Docs with clear headings |
| Parent-child | Excellent | Precise retrieval + rich context |

**Chunk Overlap Tuning**: Always include a 10-20% overlap (e.g., chunk size 500, overlap 50) to prevent cutting context mid-thought. Too small overlap = missing context at boundaries. Too large overlap = redundant retrieval and wasted tokens.

**The #1 mistake**: Using fixed-size chunking without semantic boundaries. It breaks mid-sentence, which destroys semantic meaning and embedding quality.

### 1d. Chunk Metadata

Every chunk should carry:

```json
{
  "content": "The actual text...",
  "embedding": [0.12, -0.45, ...],
  "metadata": {
    "document_id": "uuid",
    "document_name": "policy.pdf",
    "page_number": 3,
    "chunk_index": 7,
    "heading": "Refund Policy",
    "owner_id": "user_123",
    "created_at": "2024-01-15",
    "hash": "sha256:abc..."
  }
}
```

### 1e. Embedding

Use the **same model** for indexing and querying. Mixing models = garbage results.

### 1f. Deduplication

```
Document-level: SHA-256 hash of file content
  → If hash exists, skip entirely

Chunk-level: hash each chunk's text
  → Skip identical paragraphs across documents

Semantic dedup: cosine similarity > 0.98 = duplicate
  → Catches near-duplicates (minor wording changes)
```

---

## Stage 2: Retrieval

### Sparse Search (BM25 / Keyword)

```
How it works: TF-IDF weighted keyword matching.
  Counts how often query terms appear in each document.
  Weighs rare terms higher (IDF).

Good for: exact terms, product codes, case numbers
  Query: "PO-2024-0847 status"
  BM25 finds documents containing that exact string.

Bad for: semantic understanding
  Query: "How do I get money back for a broken item?"
  BM25 misses: "refund policy for damaged goods" (no word overlap)
```

### Dense Search (Vector / Embedding)

```
How it works: Embed query → cosine similarity → nearest neighbors.

Good for: semantic meaning, paraphrasing, natural language
  Query: "How do I get money back?"
  Vector search finds: "Our refund policy..." (meaning match)

Bad for: exact terms, rare identifiers
  Query: "PO-2024-0847"
  Embedding doesn't capture the specific ID well.
```

### Hybrid Search (Best Practice ⭐)

```
Run BOTH sparse and dense search, then merge results:

  BM25 results:   [doc3, doc1, doc7, doc5, doc9]
  Vector results:  [doc1, doc5, doc3, doc2, doc8]
  
  Merge with Reciprocal Rank Fusion (RRF) / Score Fusion:
    RRF_score(doc) = Σ 1/(60 + rank_k(doc))
    
    doc1: 1/62 + 1/61 = 0.033  (high in both → top result)
    doc3: 1/61 + 1/63 = 0.032
    doc5: 1/64 + 1/62 = 0.032
    
  Tools: Weaviate, Elasticsearch KNN + BM25, LangChain EnsembleRetriever
```

---

## Stage 3: Ranking

### Why Reranking Matters

Bi-encoder retrieval (the initial search) is fast but approximate. Cross-encoder reranking is slow but precise.

```
PIPELINE:
  Query → Bi-encoder → top 50 candidates (fast, recall-focused)
        → Cross-encoder reranker → top 5 (slow, precision-focused)
        → LLM

Bi-encoder: embeds query and document SEPARATELY
  ✅ Can precompute doc embeddings. Fast.
  ❌ Misses subtle query-doc interactions.

Cross-encoder: processes (query, document) as a PAIR
  ✅ Sees both simultaneously → captures nuance
  ❌ Cannot precompute. Must run for each candidate.

QUALITY IMPROVEMENT: +10-20% precision over bi-encoder-only

### Boosting (Metadata & Freshness)

Sometimes relevance isn't just semantic similarity. You want to bias the results:

```
FRESHNESS BOOSTING:
  Final_Score = Similarity_Score + (e^(decay_rate * document_age))
  → Older documents get their score slightly decayed, preferring newer ones.

METADATA BOOSTING:
  If query contains "urgent", boost documents tagged with category="troubleshooting".
  Final_Score = Similarity_Score * 1.2
```

RERANKER OPTIONS:
  • Cohere Rerank (best out-of-box, hosted)
  • ms-marco-MiniLM-L-12-v2 (open-source cross-encoder)
  • BGE Reranker (best open-source)
```

---

## Stage 4: Context Assembly

### Top-K Selection

Don't blindly send top-K chunks. Consider:

```
1. SCORE THRESHOLD: Only include chunks with similarity > 0.3
   (low-score chunks add noise, not signal)

2. DIVERSITY: If top-5 chunks are all from the same paragraph,
   you're getting redundancy, not breadth.
   Solution: MMR (Maximal Marginal Relevance) — balances relevance and diversity.

3. TOKEN BUDGET: Count tokens of assembled context.
   If top-5 chunks = 8000 tokens but your budget is 4000,
   either reduce K or compress chunks.
```

### Citation Mapping

```
When assembling context, track which chunk each fact comes from:

  Context for LLM:
    [Source: policy.pdf, p.3] "Refunds are available within 30 days."
    [Source: faq.pdf, p.1] "Software products are non-refundable."
  
  LLM response:
    "You can get a refund within 30 days [policy.pdf, p.3],
     but software is excluded [faq.pdf, p.1]."
```

---

## Stage 5: Generation

### Grounded Generation

```
SYSTEM PROMPT:
  "Answer the user's question based ONLY on the provided context.
   If the context doesn't contain the answer, say:
   'I don't have enough information to answer that.'
   Always cite your sources using [Source: filename, page]."
```

### When to Refuse

```
IF retrieval confidence is low (all chunks score < 0.3):
  → Don't hallucinate. Say: "I couldn't find relevant information."

IF chunks are contradictory:
  → Acknowledge the contradiction and cite both sources.

IF query is out of scope:
  → Refuse politely and redirect.
```

---

## Stage 6: Evaluation

### Retrieval Metrics

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Recall@K | Of all relevant docs, how many did we retrieve in top K? | > 0.85 |
| Precision@K | Of retrieved docs, how many are actually relevant? | > 0.70 |
| MRR | How high is the first relevant result? | > 0.80 |
| nDCG | Quality considering the ranking order | > 0.75 |

### Generation Metrics

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Faithfulness | Is the answer supported by the retrieved context? | > 0.90 |
| Answer Relevance | Does the answer address the user's question? | > 0.85 |
| Context Precision | Are retrieved chunks actually relevant to the query? | > 0.80 |
| Context Recall | Does retrieved context cover all aspects of the answer? | > 0.80 |

### Building a Test Set

```
1. Collect 100-500 real user questions
2. For each question, manually identify:
   - The correct answer
   - Which documents/pages contain the answer
   - Edge cases (ambiguous, unanswerable, multi-hop)
3. Run RAG pipeline on each question
4. Score retrieval + generation metrics
5. Repeat after every pipeline change (regression testing)
```

---

## Production Architecture

```
┌────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────→│  FastAPI      │────→│  PostgreSQL  │
│  (Next.js)  │     │  Backend      │     │  + pgvector  │
└────────────┘     │               │     └─────────────┘
                   │  Services:    │     ┌─────────────┐
                   │  • Upload     │────→│  File Store  │
                   │  • Extract    │     │  (S3/disk)   │
                   │  • Chunk      │     └─────────────┘
                   │  • Embed      │     ┌─────────────┐
                   │  • Search     │────→│  Embedding   │
                   │  • Generate   │     │  Model       │
                   └──────────────┘     └─────────────┘

SCALING CONSIDERATIONS:
  • Ingestion: Background workers (Celery) for large docs
  • Embedding: Batch processing, GPU acceleration
  • Search: pgvector HNSW index, connection pooling
  • Generation: Stream responses, set max_tokens
  • Monitoring: Log every query, retrieval, generation
```
