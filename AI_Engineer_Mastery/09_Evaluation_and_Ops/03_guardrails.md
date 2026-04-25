# Guardrails — Input/Output Safety Architecture

## Why Guardrails

LLMs are probabilistic. They can output toxic content, leak PII, violate policies, or produce incorrect formats. Guardrails are the **deterministic safety checks** around the probabilistic LLM core.

---

## Input Guardrails (Before LLM)

| Check | What It Catches | Implementation |
|-------|----------------|----------------|
| Length validation | Extremely long inputs (DoS) | `if len(input) > 10000: reject` |
| Language detection | Off-topic language inputs | `langdetect` library |
| PII detection | SSN, credit cards, emails in input | `presidio-analyzer` |
| Prompt injection detection | "Ignore previous instructions..." | ML classifier or regex |
| Topic classification | Off-topic queries | LLM classifier or embedding similarity |
| Rate limiting | Abuse from single user | Token bucket per user |

---

## Output Guardrails (After LLM)

| Check | What It Catches | Implementation |
|-------|----------------|----------------|
| Format validation | Invalid JSON, wrong schema | Pydantic parsing |
| PII scanning | Model leaks personal info | `presidio-analyzer` on output |
| Toxicity check | Offensive or harmful content | `detoxify` or Perspective API |
| Policy compliance | Answers violating business rules | Custom rule engine |
| Hallucination check | Claims not supported by context | Faithfulness scorer |
| Factual validation | Incorrect dates, numbers | Regex + domain rules |

---

## Layered Architecture

```
USER INPUT
    │
    ▼
┌──────────────────┐
│ INPUT GUARDRAILS  │ ← PII removal, injection detection, length check
└────────┬─────────┘
         ▼
┌──────────────────┐
│ LLM CALL          │ ← System prompt with safety instructions
└────────┬─────────┘
         ▼
┌──────────────────┐
│ OUTPUT GUARDRAILS │ ← PII scan, toxicity, format validation
└────────┬─────────┘
         ▼
    RESPONSE TO USER
```

---

## Tools

| Tool | Focus |
|------|-------|
| **guardrails-ai** | Output validation with auto-retry |
| **NeMo Guardrails (NVIDIA)** | Programmable safety rails, topic control |
| **LLM Guard** | Input/output scanning for LLM apps |
| **Presidio** | PII detection and redaction |
| **Rebuff** | Prompt injection detection |

---

## Production Pattern

```python
async def safe_generate(query: str, context: str) -> str:
    # INPUT GUARDRAILS
    if detect_injection(query):
        return "I can only help with product questions."
    query = redact_pii(query)
    
    # LLM CALL
    response = await llm.generate(query, context)
    
    # OUTPUT GUARDRAILS
    response = redact_pii(response)
    if detect_toxicity(response):
        return "I'm unable to provide that response."
    if not validate_json(response):
        response = await retry_with_repair(response)
    
    return response
```
