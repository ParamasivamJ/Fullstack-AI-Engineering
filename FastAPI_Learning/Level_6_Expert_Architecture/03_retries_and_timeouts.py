"""
Level 6 — Retries, Timeouts, and Fallbacks
============================================

LLM APIs are unreliable. They return 429 (rate limited) and 503 (unavailable).
They time out. They return garbage. You must design for this from the start.

This file teaches:
  1. Timeouts — never wait forever for an LLM
  2. Retries with exponential backoff — automatically handle transient errors
  3. Fallback models — if primary fails, try a cheaper backup
  4. Circuit breaker — stop calling a service that keeps failing

HOW TO RUN:
  pip install httpx tenacity
  uvicorn 03_retries_and_timeouts:app --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import httpx
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)

app = FastAPI(title="Level 6: Retries and Timeouts")


# ─────────────────────────────────────────────
# 1. TIMEOUT PATTERNS
# ─────────────────────────────────────────────

TIMEOUTS = httpx.Timeout(
    connect=5.0,    # max time to establish connection
    read=30.0,      # max time to receive any data after connection
    write=10.0,     # max time to send request body
    pool=5.0,       # max time waiting for a connection from the pool
)

async def call_llm_with_timeout(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Wraps an LLM call with a strict timeout using asyncio.wait_for."""
    try:
        result = await asyncio.wait_for(
            _simulate_llm_call(prompt, latency=1.5),
            timeout=10.0,   # fail fast — never hang a user for more than 10 seconds
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"LLM call timed out after 10s | model={model}")
        raise HTTPException(
            status_code=504,
            detail="The AI model took too long to respond. Please try again.",
        )


async def _simulate_llm_call(prompt: str, latency: float = 1.5, fail: bool = False) -> str:
    """Simulates an LLM API call with configurable latency and failures."""
    await asyncio.sleep(latency)
    if fail:
        raise httpx.HTTPStatusError(
            "Service Unavailable",
            request=None,  # type: ignore
            response=httpx.Response(503),
        )
    return f"Answer to: {prompt[:50]}..."


# ─────────────────────────────────────────────
# 2. MANUAL RETRY WITH EXPONENTIAL BACKOFF
# ─────────────────────────────────────────────
# Exponential backoff: wait 1s, then 2s, then 4s between retries.
# This prevents hammering a struggling service.

async def call_llm_with_retry(
    prompt: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
) -> str:
    """
    Retries an LLM call up to max_attempts times with exponential backoff.

    Retryable errors: 429 (rate limited), 5xx (server errors)
    Non-retryable:    4xx (client errors like 400, 401, 403, 404)
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"LLM attempt {attempt}/{max_attempts}")
            result = await _simulate_llm_call(prompt)
            return result

        except httpx.HTTPStatusError as e:
            last_exception = e

            if e.response.status_code not in retryable_status_codes:
                # Do NOT retry client errors (4xx) — they will always fail
                logger.error(f"Non-retryable error: {e.response.status_code}")
                raise

            if attempt < max_attempts:
                # Exponential backoff: 1s, 2s, 4s...
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed ({e.response.status_code}). Retrying in {delay}s...")
                await asyncio.sleep(delay)

        except asyncio.TimeoutError as e:
            last_exception = e
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} timed out. Retrying in {delay}s...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(f"All {max_attempts} attempts failed")
    raise HTTPException(status_code=502, detail="AI service is currently unavailable. Please try again later.")


# ─────────────────────────────────────────────
# 3. FALLBACK MODEL PATTERN
# ─────────────────────────────────────────────
# If the primary (expensive) model fails, try the fallback (cheaper) model.
# This keeps the app working even during partial outages.

MODEL_PRIORITY = ["gpt-4o", "gpt-4o-mini"]  # try expensive first, fall back to cheap

async def call_with_fallback(prompt: str) -> dict:
    """
    Tries each model in priority order.
    Returns the first successful result.
    """
    errors = []

    for model in MODEL_PRIORITY:
        try:
            logger.info(f"Trying model: {model}")
            result = await asyncio.wait_for(
                _simulate_llm_call(prompt),
                timeout=15.0,
            )
            return {"answer": result, "model_used": model, "fallback": model != MODEL_PRIORITY[0]}

        except (asyncio.TimeoutError, httpx.HTTPStatusError) as e:
            errors.append({"model": model, "error": str(e)})
            logger.warning(f"Model {model} failed: {e}")
            continue

    # All models failed
    raise HTTPException(
        status_code=503,
        detail={
            "message": "All AI models are currently unavailable",
            "tried": [e["model"] for e in errors],
        },
    )


# ─────────────────────────────────────────────
# 4. CIRCUIT BREAKER (simplified)
# ─────────────────────────────────────────────
# A circuit breaker stops calling a failing service for a cool-down period.
# This prevents cascading failures and gives the service time to recover.

class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal: requests flow through
    OPEN = "open"          # Tripped: requests fail immediately without calling the service
    HALF_OPEN = "half_open" # Testing: one request goes through to check if service recovered


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold   # trips after this many consecutive failures
        self.recovery_timeout = recovery_timeout      # seconds before trying again
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.state = CircuitState.CLOSED

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit OPEN after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit HALF-OPEN: testing recovery")
                return True
            return False
        return True  # HALF_OPEN: allow one test request


# Singleton circuit breaker for the LLM service
llm_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


async def call_llm_with_circuit_breaker(prompt: str) -> str:
    if not llm_circuit.can_attempt():
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable. Please try again in 30 seconds.",
        )
    try:
        result = await _simulate_llm_call(prompt)
        llm_circuit.record_success()
        return result
    except Exception as e:
        llm_circuit.record_failure()
        raise HTTPException(status_code=502, detail="AI service error")


# ─────────────────────────────────────────────
# DEMO ENDPOINTS
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

@app.post("/chat/timeout-demo", tags=["Resilience"])
async def chat_with_timeout(req: ChatRequest):
    answer = await call_llm_with_timeout(req.message)
    return {"answer": answer}

@app.post("/chat/retry-demo", tags=["Resilience"])
async def chat_with_retry(req: ChatRequest):
    answer = await call_llm_with_retry(req.message)
    return {"answer": answer}

@app.post("/chat/fallback-demo", tags=["Resilience"])
async def chat_with_fallback(req: ChatRequest):
    return await call_with_fallback(req.message)

@app.post("/chat/circuit-demo", tags=["Resilience"])
async def chat_circuit(req: ChatRequest):
    answer = await call_llm_with_circuit_breaker(req.message)
    return {"answer": answer, "circuit_state": llm_circuit.state}

@app.get("/circuit/status", tags=["Resilience"])
def circuit_status():
    return {
        "state": llm_circuit.state,
        "failure_count": llm_circuit.failure_count,
        "threshold": llm_circuit.failure_threshold,
    }
