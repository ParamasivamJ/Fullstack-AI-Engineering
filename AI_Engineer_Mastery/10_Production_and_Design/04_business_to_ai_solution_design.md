# Business Requirements → AI Solution Design

## The Career-Defining Skill

The hardest skill in AI engineering is **translating a business requirement into the right architecture**. This separates juniors who build demos from seniors who ship products.

---

## The Decision Framework

```
Q1: Need CURRENT facts from specific documents?
    YES → RAG
Q2: Need MULTIPLE STEPS with tool use?
    YES → Agent or orchestrated workflow
Q3: Do steps VARY based on intermediate results?
    YES → Agent (dynamic)  /  NO → Deterministic workflow
Q4: Need specific FORMAT or STYLE consistently?
    YES → Fine-tuning
Q5: Knowledge STABLE or CHANGING?
    CHANGING → RAG  /  STABLE → Fine-tuning might suffice
```

---

## Real-World Scenarios

| Requirement | Architecture | Why |
|------------|-------------|-----|
| Search 50K legal contracts with citations | RAG + hybrid retrieval + reranking | Current facts, citations, large corpus |
| Classify emails into 8 categories | Fine-tuned Llama-8B | Fixed task, high volume, low cost |
| Research companies for due diligence | Multi-agent (researcher + analyst + writer) | Multi-step, web search, iterative |
| Generate marketing copy in brand voice | Fine-tuned GPT-4o-mini | Style consistency, no retrieval needed |
| Customer product troubleshooting | RAG + fine-tuned model + guardrails | Docs (RAG) + tone (fine-tune) + safety |
| Weekly sales data reports | Deterministic chain (SQL → LLM → template) | Fixed steps, no dynamic planning |

---

## Architecture Decision Record (ADR)

When proposing an architecture, document:

```
DECISION: Use RAG + hybrid retrieval for legal Q&A

ALTERNATIVES CONSIDERED:
  1. Fine-tune on legal corpus
     ✗ Rejected: corpus changes monthly, no citations
  2. Pure vector search
     ✗ Rejected: legal terms need exact matching
  3. Hybrid (BM25 + vector) + reranking
     ✓ Selected: handles semantic + exact matching

TRADEOFFS ACCEPTED:
  • +200ms latency from reranking
  • +$0.002/query for reranker API
  • Weekly re-indexing required

QUALITY TARGETS:
  • Recall@10 > 0.85
  • Faithfulness > 0.90
  • P95 latency < 3 seconds

FALLBACK:
  If retrieval confidence < 0.3:
  "I couldn't find a definitive answer. Related docs: [links]"
```

---

## The Interview Framework

1. **Clarify**: "What's the query volume? How often does data change? Latency budget? Internal or external users?"
2. **Propose with justification**: "I'd use RAG because the corpus changes monthly and we need citations."
3. **Address quality**: "I'd measure recall@10 and faithfulness with a 200-question test set."
4. **Address production**: "Route simple queries to GPT-4o-mini, complex to GPT-4o. Log everything for drift detection."
5. **Show demo→production path**: "MVP in 2 weeks, add reranking month 2, monitoring month 3."

---

## Communicating with Non-Technical Stakeholders

**Instead of**: "We use cosine similarity over 384-dimensional embeddings with HNSW indexing for grounded generation."

**Say**: "The system finds the most relevant paragraphs from your documents when someone asks a question, then writes an answer with page references so you can verify."

---

## The Gold Standard

> The engineer who can explain *why* they chose RAG over fine-tuning, *why* hybrid search over pure vector, and *what happens when it fails* — that's who companies fight to hire.
