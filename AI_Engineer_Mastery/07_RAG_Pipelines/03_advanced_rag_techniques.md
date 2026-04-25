# Advanced RAG Techniques — Production Patterns

## Why Naive RAG Fails

Naive RAG: embed query → cosine similarity → top-K → LLM. Fails when: (1) query uses different vocabulary, (2) answer spans multiple chunks, (3) query is vague, (4) context is in surrounding text, not the retrieved chunk.

---

## Technique 1: Hybrid Search (BM25 + Vector)

```
BM25 catches: exact terms ("PO-2024-0847")
Vector catches: semantic meaning ("How do I get money back?")

MERGE WITH RRF:
  RRF_score(doc) = Σ 1/(60 + rank_k(doc))

  doc A: vector rank=1, BM25 rank=5 → 1/61 + 1/65 = 0.032
  doc B: vector rank=3, BM25 rank=1 → 1/63 + 1/61 = 0.032

Tools: Weaviate hybrid, Elasticsearch KNN+BM25, LangChain EnsembleRetriever
```

---

## Technique 2: Query Rewriting

```
User: "Tell me more about that"
→ LLM rewrites: "What is the return policy for software products?"
→ Retrieve with rewritten query

Cost: one cheap LLM call. Quality gain: significant for multi-turn chat.
```

---

## Technique 3: Multi-Query Expansion

```
Original: "How does machine learning work?"
Variants: ["ML algorithm fundamentals", "Training AI models", "Computers learn from data"]

Retrieve top-5 per variant → 15 candidates → deduplicate → rerank → top-5
Recall improvement: 20-40%
```

---

## Technique 4: HyDE (Hypothetical Document Embedding)

```
Problem: questions and answers embed differently.

Step 1: LLM generates hypothetical answer (no retrieval)
Step 2: Embed the HYPOTHETICAL ANSWER
Step 3: Retrieve chunks similar to the hypothetical answer

Works because: hypothetical answer is stylistically similar to real docs.
```

---

## Technique 5: Parent-Child Chunking

```
INDEXING:
  Parent chunks: 1024 tokens (rich context)
  Child chunks: 128 tokens (precise retrieval)
  Index ONLY child embeddings

RETRIEVAL:
  Find similar CHILDREN (precise!) → map to PARENTS (rich context!)

Result: pinpoint retrieval + full context for generation.
LangChain: ParentDocumentRetriever
```

---

## Technique 6: Late Reranking

```
Bi-encoder → top 50 (fast, recall-focused)
Cross-encoder → top 5 (slow, precision-focused)

Reranker options: Cohere Rerank, ms-marco-MiniLM, BGE Reranker
Quality: +10-20% precision over bi-encoder only
```

---

## Technique 7: Context Compression

```
Retrieved chunk: 1024 tokens (mostly irrelevant)
Compressed chunk: 30 tokens (only relevant sentences)

LLM extracts: "Only sentences relevant to: [query]"
90% token reduction. Better generation quality.

LangChain: ContextualCompressionRetriever + LLMChainExtractor
```

---

## Technique 8: Multi-Hop Retrieval

```
Query: "Compare Company A's Q3 revenue with Company B's Q3 revenue"

Step 1: Retrieve Company A's financials
Step 2: Retrieve Company B's financials (INFORMED by step 1)
Step 3: Compare both in LLM context

One retrieval can't get both — need sequential retrieval steps.
```

---

## Technique 9: Metadata Filtering

```sql
-- Pre-filter BEFORE vector search (faster, more precise)
-- Common filter types:
--   • Tenant: owner_id = 'user_123' (critical for security)
--   • Time/Freshness: created_at > '2024-01-01'
--   • Domain/Source: department = 'legal' OR source = 'confluence'
--   • Version: doc_version = 'latest'
--   • Permissions: access_level <= user_clearance

SELECT * FROM chunks
WHERE owner_id = 'user_123'          
  AND content_type = 'application/pdf' 
  AND created_at > '2024-01-01'      
ORDER BY embedding <=> query_vec
LIMIT 5;
```

---

## Technique 10: Query Decomposition

```
Complex Query: "How does the 2024 tax code change affect our Q3 vs Q4 revenue projections?"

Decomposition (via LLM):
  1. "What are the key changes in the 2024 tax code?"
  2. "What were the Q3 revenue projections?"
  3. "What were the Q4 revenue projections?"

Execute 3 separate retrievals → Combine context → Answer final question.
Works best for questions requiring multiple distinct facts.
```

---

## Technique 11: Hierarchical Retrieval

```
Retrieval is done in stages (from coarse to fine):

Step 1 (Document Level): Match query against document summaries
  → Find "Annual Report 2024"
Step 2 (Section Level): Match query against section summaries within the doc
  → Find "Tax Strategy" section
Step 3 (Chunk Level): Match query against specific chunks in that section
  → Find chunk 42 with exact numbers

Saves computation (don't embed/search chunks of irrelevant documents) and 
maintains logical hierarchy of the information.
```

---

## Fallback When Retrieval Fails

```
High confidence (>0.5):  Normal response with citations
Medium (0.3-0.5):       Response + "Based on limited information..."
Low (<0.3):             "I couldn't find a definitive answer."
No results:             "Would you like me to search differently?"
```
