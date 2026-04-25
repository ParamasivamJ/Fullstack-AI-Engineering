# Fallback & Degradation Strategies

## Why Fallback Is the Strongest Production Maturity Signal

In an interview, when you describe a system that "gracefully degrades when things fail," you signal production experience. Every component in an AI pipeline CAN fail — and WILL fail at scale.

---

## Failure Points in an AI Pipeline

| Component | What Can Fail | Frequency |
|-----------|--------------|-----------|
| LLM API | Rate limits, outages, timeout | Weekly |
| Embedding API | Same as above | Weekly |
| Vector DB | Connection issues, slow queries | Monthly |
| Retrieval | No relevant results found | 5-15% of queries |
| Structured output | Invalid JSON, wrong schema | 2-5% of requests |
| Tool calls | External APIs down, errors | Daily |
| Reranker | Service down, timeout | Monthly |

---

## Fallback Strategies

### 1. Model Fallback

```
PRIMARY:   GPT-4o (best quality)
    │
    ▼ if fails (timeout, 429, 500)
SECONDARY: Claude 3.5 Sonnet (different provider)
    │
    ▼ if fails
TERTIARY:  GPT-4o-mini (degraded quality, but responds)
    │
    ▼ if ALL fail
STATIC:    "I'm temporarily unable to process your request. 
            Please try again in a few minutes."
```

### 2. Retrieval Fallback

```
HIGH confidence (score > 0.5):
  → Normal RAG response with citations

MEDIUM confidence (0.3 < score < 0.5):
  → Response with disclaimer: "Based on limited information..."

LOW confidence (score < 0.3):
  → "I couldn't find a definitive answer. Here are related 
     documents you might review: [links]"

NO results:
  → "I don't have information about that topic. 
     Would you like me to search differently?"
```

### 3. Structured Output Fallback

```
Attempt 1: Parse LLM response as JSON
  → Success: return parsed result

Attempt 2: Strip markdown wrapping, retry parse
  → "```json\n{...}\n```" → extract inner JSON

Attempt 3: Send error back to LLM for self-repair
  → "Fix this JSON: {broken}. Error: {error}"

Attempt 4: Return raw text with error flag
  → {"raw_text": "...", "parse_failed": true}
  → Frontend shows the text, logs the failure for review
```

### 4. Tool Failure Fallback

```
Tool call fails → Retry once with exponential backoff
  → Still fails → Try alternative tool (if available)
  → No alternative → Respond without tool result:
    "I wasn't able to check the current status, but based on 
     our general policy: [answer from knowledge]"
```

---

## Degradation Levels

```
LEVEL 0 (FULL SERVICE):
  All components working. Full RAG + reranking + generation.
  
LEVEL 1 (MINOR DEGRADATION):
  Reranker down → skip reranking, use bi-encoder results only.
  Quality slightly lower, but functional.

LEVEL 2 (SIGNIFICANT DEGRADATION):
  Primary LLM down → route to backup model.
  Slower or lower quality, but still working.

LEVEL 3 (EMERGENCY MODE):
  LLM + vector DB both down → serve cached FAQ responses.
  Very limited, but users aren't completely blocked.

LEVEL 4 (MAINTENANCE MODE):
  Everything down → static "under maintenance" page.
  Log queries for processing when service restores.
```

---

## Implementation Pattern

```python
async def answer_query(query: str) -> Response:
    try:
        # Full pipeline
        chunks = await retrieve(query)
        reranked = await rerank(query, chunks)
        answer = await generate(query, reranked)
        return Response(answer=answer, degraded=False)
    
    except RerankerError:
        # Degrade: skip reranking
        answer = await generate(query, chunks)
        return Response(answer=answer, degraded=True, 
                       note="Results may be less precise")
    
    except LLMError:
        try:
            # Fallback model
            answer = await generate_fallback(query, chunks)
            return Response(answer=answer, degraded=True,
                           note="Using backup model")
        except:
            return Response(answer="Service temporarily unavailable",
                           degraded=True, error=True)
    
    except RetrievalError:
        return Response(
            answer="I couldn't search the knowledge base right now.",
            degraded=True, suggest_retry=True)
```

---

## Production Checklist

- [ ] Every external call has a timeout (5s default)
- [ ] Every external call has a retry with exponential backoff
- [ ] Primary → secondary → tertiary model chain defined
- [ ] Low-confidence retrieval returns disclaimer, not hallucination
- [ ] Structured output has 3-attempt repair loop
- [ ] All fallback events are logged with reason codes
- [ ] Degradation level is exposed in health endpoint
- [ ] Cached FAQ responses available for complete outage
