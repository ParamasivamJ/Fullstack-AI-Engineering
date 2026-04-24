# AI Production Patterns — Quick Reference

## Pattern 1: RAG (Retrieval-Augmented Generation)
```
Question → Embed → Search Vector DB → Build Prompt → LLM → Answer + Sources
```
**When:** User asks questions over a knowledge base (docs, manuals, policies).
**Key rules:** Always include sources. Always have a "no context" fallback. Never hallucinate.

---

## Pattern 2: Streaming Chat
```
Request → Validate → Call LLM (stream=True) → Yield SSE tokens → done event
```
**When:** Any user-facing chat interface.
**Frontend:** EventSource API with `event: message` / `event: done` / `event: error`.

---

## Pattern 3: Document Ingestion
```
Upload → Validate → Save → Return 201 → [Background] Extract → Chunk → Embed → Store
```
**When:** Users upload PDFs/DOCX to build a knowledge base.
**Key:** Always return immediately. Index in background. Notify via status polling or webhook.

---

## Pattern 4: Cost Control Stack
1. **Input limit:** `max_length=4000` in Pydantic (line 1 defense)
2. **Token estimation:** `len(text) // 4` before calling LLM
3. **Model routing:** free tier → mini model, pro → full model
4. **Caching:** `sha256(model + question.lower())` → Redis/in-memory
5. **Output cap:** `max_tokens=1000` on every LLM call

---

## Pattern 5: Retry with Backoff
```python
import httpx, asyncio

for attempt in range(3):
    try:
        resp = await client.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (429, 503) and attempt < 2:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
        else:
            raise
```

---

## Pattern 6: Per-User Rate Limiting
```python
# In middleware or dependency:
user_key = f"rate:{user_id}"
count = redis.incr(user_key)
if count == 1:
    redis.expire(user_key, 60)  # 1-minute window
if count > 60:
    raise HTTPException(429, "Too many requests")
```

---

## Pattern 7: Structured LLM Output
```python
from pydantic import BaseModel

class AnalysisOutput(BaseModel):
    summary: str
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float

# OpenAI structured output:
response = openai.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[...],
    response_format=AnalysisOutput,  # forces valid JSON matching schema
)
result = response.choices[0].message.parsed  # already a Pydantic object!
```

---

## Pattern 8: Observability Trio
Every AI request should log 3 things:
```python
logger.info({
    "event": "llm_call",
    "request_id": req.state.request_id,  # from middleware
    "user_id": current_user.id,
    "model": model_name,
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "latency_ms": elapsed_ms,
    "cost_usd": estimated_cost,
    "cache_hit": was_cached,
})
```

---

## Pattern 9: Graceful Fallback
```python
async def call_primary_llm(prompt):   # expensive, capable
    ...

async def call_fallback_llm(prompt):  # cheap, less capable
    ...

try:
    return await asyncio.wait_for(call_primary_llm(prompt), timeout=20)
except (asyncio.TimeoutError, Exception):
    logger.warning("Primary LLM failed, falling back")
    return await call_fallback_llm(prompt)
```

---

## Pattern 10: Tenant Isolation (Multi-User)
Always add `owner_id` filter to EVERY query:
```python
# ✅ CORRECT — user can only see their own data
query = select(Task).where(Task.owner_id == current_user.id)

# ❌ WRONG — returns ALL users' data
query = select(Task)
```
Use a dependency that automatically scopes queries to the current user.
