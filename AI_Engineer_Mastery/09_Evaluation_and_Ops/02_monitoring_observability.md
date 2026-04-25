# Monitoring & Observability for Production LLMs

## What to Log

Every LLM request should produce a trace record:

```json
{
  "request_id": "uuid",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": "user_123",
  "model": "gpt-4o",
  "prompt_version": "v2.1",
  "input_tokens": 4600,
  "output_tokens": 800,
  "cost_usd": 0.035,
  "latency_ms": 1800,
  "retrieval": {
    "query": "What is the return policy?",
    "chunks_retrieved": 5,
    "top_score": 0.87,
    "retrieval_latency_ms": 50
  },
  "output_validation": {
    "json_valid": true,
    "policy_compliant": true,
    "pii_detected": false
  }
}
```

---

## Drift Detection

| Type | What Changes | Detection |
|------|-------------|-----------|
| Data drift | User queries change over time | Monitor query embedding clusters |
| Model drift | API provider updates model | Track quality scores weekly |
| Performance drift | Latency increases gradually | P95 latency trending |
| Quality drift | Answer quality decreases | Faithfulness score sampling |

---

## Tools

| Tool | Purpose | Open Source? |
|------|---------|-------------|
| **LangSmith** | Full LLM tracing, prompt management | No (LangChain) |
| **Langfuse** | LLM observability, cost tracking | ✅ Yes |
| **Helicone** | LLM request logging, analytics | ✅ Yes |
| **OpenTelemetry** | General observability, works with LLM spans | ✅ Yes |
| **Datadog / New Relic** | Enterprise monitoring with LLM plugins | No |

---

## Alert Rules

```
CRITICAL:
  - Error rate > 5% in 5 minutes → page on-call
  - All LLM providers down → activate fallback mode

WARNING:
  - P95 latency > 5 seconds → investigate
  - Daily cost > 120% budget → review
  - Faithfulness score < 0.8 (sampled) → review prompts

INFO:
  - Cache hit rate < 10% → check cache health
  - New query patterns detected → review test coverage
```
