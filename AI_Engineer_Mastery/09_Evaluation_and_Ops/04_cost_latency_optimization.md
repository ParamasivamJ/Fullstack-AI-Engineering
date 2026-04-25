# Cost & Latency Optimization — Production Economics

## Why This Matters

A POC costs $5/day. Production at scale costs $5,000/day. The difference between a successful AI product and a cancelled one is often cost optimization.

---

## Token Cost Breakdown

```
TYPICAL RAG REQUEST:
  System prompt:       500 tokens  × $0.005/1K = $0.0025
  Retrieved context:  3000 tokens  × $0.005/1K = $0.0150
  Conversation history:1000 tokens × $0.005/1K = $0.0050
  User query:          100 tokens  × $0.005/1K = $0.0005
  ─────────────────────────────────────────────
  Input total:        4600 tokens               = $0.0230
  
  Output response:     800 tokens  × $0.015/1K = $0.0120
  ─────────────────────────────────────────────
  TOTAL PER REQUEST:                            = $0.0350

  At 100K requests/day = $3,500/day = $105K/month
```

---

## Optimization Strategies

### 1. Reduce Token Usage

| Technique | Savings | Effort |
|-----------|---------|--------|
| Shorter system prompt | 10-20% | Low |
| Fewer retrieved chunks (5 → 3) | 20-40% | Low |
| Context compression | 50-80% | Medium |
| Trim conversation history | 10-30% | Low |
| Fine-tune instructions into model | 30-50% | High |

### 2. Model Routing (Biggest Win)

```
Route by complexity:

  Simple queries (80%):  GPT-4o-mini  → $0.003/request
  Medium queries (18%):  GPT-4o       → $0.035/request
  Complex queries (2%):  GPT-4o + CoT → $0.070/request

  WEIGHTED AVERAGE: $0.003×0.8 + $0.035×0.18 + $0.070×0.02
                  = $0.0024 + $0.0063 + $0.0014
                  = $0.0101/request

  vs all-GPT-4o:   $0.035/request
  SAVINGS: 71%
```

### 3. Caching

```
EMBEDDING CACHE:
  Same query text → same embedding vector
  Cache key: SHA-256(query_text)
  Hit rate: 15-30% for FAQ-heavy applications

RESPONSE CACHE:
  Identical (or near-identical) queries → cached response
  Cache key: SHA-256(query + context)
  Hit rate: 5-15% typically
  
  ⚠️ Only cache when freshness doesn't matter.
  Don't cache time-sensitive or user-specific answers.

LLM RESPONSE CACHE:
  Some providers (Anthropic, OpenAI) offer prompt caching:
  - Cache the system prompt prefix
  - Only pay full price for the dynamic parts
  - Savings: 50-90% on input tokens for repeat system prompts
```

### 4. Streaming for Perceived Latency

```
WITHOUT streaming:
  User waits 3 seconds → sees complete response.
  Perceived: "This is slow."

WITH streaming:
  User sees first token in 200ms → text flows in over 3 seconds.
  Perceived: "This is responsive!"
  
  Total time is the same. Perceived experience is dramatically better.
```

---

## Latency Breakdown

```
TYPICAL RAG REQUEST LATENCY:

  Embed query:           30ms   (embedding model)
  Vector search:         20ms   (pgvector HNSW)
  Reranking:            150ms   (cross-encoder)
  LLM generation:      1500ms   (GPT-4o, 800 tokens)
  Network overhead:     100ms   (API round-trip)
  ──────────────────────────────
  TOTAL:               1800ms

OPTIMIZATION TARGETS:
  1. Reranking: use smaller cross-encoder or skip for simple queries
  2. LLM: use smaller model for easy queries
  3. Parallel: embed query while preparing prompt
  4. Streaming: return first token in 200ms even if total is 2s
```

### Measure Every Stage

```python
import time

stages = {}

t = time.perf_counter()
query_embedding = embed(query)
stages["embed"] = time.perf_counter() - t

t = time.perf_counter()
chunks = vector_search(query_embedding)
stages["search"] = time.perf_counter() - t

t = time.perf_counter()
reranked = rerank(query, chunks)
stages["rerank"] = time.perf_counter() - t

t = time.perf_counter()
answer = llm_generate(query, reranked)
stages["generate"] = time.perf_counter() - t

# Log: {"embed": 0.03, "search": 0.02, "rerank": 0.15, "generate": 1.5}
# Now you know WHERE to optimize.
```

---

## Cost Monitoring Dashboard

```
TRACK DAILY:
  • Total tokens consumed (input + output)
  • Cost per model tier
  • Cost per user/tenant
  • Cost per feature (search, summarize, classify)
  • Cache hit rate
  • Queries routed to each model tier

SET ALERTS:
  • Daily cost exceeds budget × 1.2 → alert
  • Single user exceeds 10x average → investigate (abuse?)
  • Cache hit rate drops below 10% → check cache health
```
