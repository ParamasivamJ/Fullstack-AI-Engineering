# AI Quality Metrics — Measuring LLM Systems

## Why Metrics Matter

You can't improve what you can't measure. In production AI, "it seems to work" is not enough. You need quantifiable metrics that you track over time, alert on regressions, and present to stakeholders.

---

## Retrieval Metrics

| Metric | Formula | What It Measures | Target |
|--------|---------|-----------------|--------|
| **Recall@K** | relevant_retrieved / total_relevant | Of all relevant docs, how many did we find in top K? | > 0.85 |
| **Precision@K** | relevant_retrieved / K | Of retrieved docs, how many are actually relevant? | > 0.70 |
| **MRR** | 1 / rank_of_first_relevant | How high is the first relevant result? | > 0.80 |
| **nDCG** | DCG / ideal_DCG | Quality considering the ranking order | > 0.75 |

### Practical Example

```
Query: "What is the return policy?"
Relevant documents: [doc3, doc7, doc12]

Retrieved top-5: [doc3, doc5, doc7, doc1, doc12]

Recall@5:    3/3 = 1.0  (found all 3 relevant docs)
Precision@5: 3/5 = 0.6  (2 of 5 retrieved were irrelevant)
MRR:         1/1 = 1.0  (first relevant doc is rank 1)
```

---

## Generation Metrics

| Metric | What It Measures | How to Compute |
|--------|-----------------|----------------|
| **Faithfulness** | Is the answer supported by retrieved context? | LLM-as-judge: "Does this context support this claim?" |
| **Answer Relevance** | Does the answer address the question? | LLM-as-judge or semantic similarity |
| **Completeness** | Does the answer cover all aspects? | Compare against gold answer |
| **Factuality** | Are stated facts correct? | Fact-checking against source documents |

### LLM-as-Judge Pattern

```
JUDGE PROMPT:
  "Given the following context and answer, rate faithfulness 0-1.
   
   Context: {retrieved_context}
   Answer: {model_answer}
   
   Score 1.0 if every claim in the answer is supported by the context.
   Score 0.0 if the answer contains information not in the context.
   Score 0.5 if partially supported.
   
   Return JSON: {"score": 0.X, "reasoning": "..."}"
```

---

## Task-Specific Metrics

| Metric | Use Case |
|--------|----------|
| Exact Match | Classification, entity extraction |
| F1 Score | Token-level overlap between predicted and gold |
| Pass/Fail | Binary success criteria (did it complete the task?) |
| Human Rating | 1-5 scale rubric rated by domain experts |
| BLEU/ROUGE | Machine translation, summarization (legacy) |

---

## Safety Metrics

| Metric | What It Measures | Tools |
|--------|-----------------|-------|
| Toxicity rate | % of outputs containing toxic content | Perspective API, HuggingFace toxicity classifier |
| Policy violations | % of outputs breaking business rules | Custom classifiers |
| PII leakage | % of outputs containing personal info | Presidio, regex patterns |
| Injection success rate | % of adversarial inputs that bypass safety | Red team testing |

---

## Business Metrics (What Leadership Cares About)

| Metric | What It Measures |
|--------|-----------------|
| Resolution rate | % of queries successfully answered |
| Deflection rate | % of support tickets avoided by AI |
| Task completion | % of user tasks completed via AI |
| User satisfaction | CSAT/NPS after AI interaction |
| Cost per resolution | Total AI cost / successful resolutions |
| Time to resolution | Average time from query to answer |

---

## Building an Evaluation Pipeline

```
1. COLLECT TEST SET
   - 200-500 real user queries
   - Gold answers from domain experts
   - Identify which documents contain the answers

2. RUN PIPELINE
   For each query:
     - Run retrieval → record retrieved chunks
     - Run generation → record answer
     - Score retrieval metrics (recall, precision, MRR)
     - Score generation metrics (faithfulness, relevance)

3. TRACK OVER TIME
   Store scores per version:
     v1.0: recall=0.82, faithfulness=0.88
     v1.1: recall=0.87, faithfulness=0.91  ← improvement!
     v2.0: recall=0.85, faithfulness=0.84  ← regression in faithfulness!

4. ALERT ON REGRESSIONS
   If any metric drops > 5% from previous version → block deployment.
```

---

## Production Monitoring Dashboard

```
REAL-TIME METRICS:
  • Requests/minute
  • P50/P95/P99 latency
  • Error rate
  • Average token usage per request
  • Cost per hour

QUALITY METRICS (sampled):
  • Faithfulness score (LLM-judge on 5% of requests)
  • User feedback (thumbs up/down)
  • Escalation rate (AI → human handoff)
  
ALERTS:
  • Latency P95 > 5 seconds → investigate
  • Error rate > 2% → page on-call
  • Faithfulness score drops below 0.8 → block new deployments
```
