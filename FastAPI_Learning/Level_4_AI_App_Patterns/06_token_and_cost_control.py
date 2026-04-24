"""
Level 4 — Token and Cost Control (Critical for AI Apps)
=========================================================

Every LLM call costs money. Every second of latency loses users.
This file teaches the engineering patterns that control both.

Expert AI engineers ALWAYS think about cost and latency from day one.
Retrofitting cost controls into a running app is painful and risky.

HOW TO RUN:
  uvicorn 06_token_and_cost_control:app --reload
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import time
import hashlib
import json

app = FastAPI(title="Level 4: Cost and Token Control")


# ─────────────────────────────────────────────
# MODEL ROUTING TABLE
# ─────────────────────────────────────────────
# Different models have different costs and capabilities.
# Route requests to the cheapest model that can handle them.

MODEL_CONFIG = {
    "gpt-4o-mini": {
        "cost_per_1k_input": 0.00015,   # $0.00015 per 1000 input tokens
        "cost_per_1k_output": 0.0006,
        "max_context": 128_000,
        "tier_required": "free",         # available to all users
    },
    "gpt-4o": {
        "cost_per_1k_input": 0.0025,
        "cost_per_1k_output": 0.010,
        "max_context": 128_000,
        "tier_required": "pro",          # only for paid users
    },
    "claude-3-5-sonnet": {
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "max_context": 200_000,
        "tier_required": "pro",
    },
}


# ─────────────────────────────────────────────
# SIMPLE CACHE (in production, use Redis)
# ─────────────────────────────────────────────
# Caching is one of the highest-ROI optimizations in AI apps.
# Same question, same cached answer → zero LLM cost, zero latency.

response_cache: dict = {}

def get_cache_key(question: str, model: str) -> str:
    """Creates a unique key for a question+model combination."""
    # Use a hash so the key is short and consistent regardless of spacing/case
    content = f"{model}:{question.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def get_from_cache(key: str) -> Optional[dict]:
    """Returns cached response if it exists and is not expired."""
    if key in response_cache:
        entry = response_cache[key]
        # Cache expires after 1 hour (3600 seconds)
        if time.time() - entry["timestamp"] < 3600:
            return entry["data"]
        # Expired — remove it
        del response_cache[key]
    return None

def save_to_cache(key: str, data: dict):
    """Saves a response to cache with the current timestamp."""
    response_cache[key] = {"data": data, "timestamp": time.time()}


# ─────────────────────────────────────────────
# TOKEN ESTIMATION
# ─────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """
    Rough token estimation without calling tiktoken.
    Rule of thumb: 1 token ≈ 4 characters ≈ 0.75 words.
    For exact counts: pip install tiktoken, then:
      import tiktoken
      enc = tiktoken.encoding_for_model("gpt-4o")
      return len(enc.encode(text))
    """
    return len(text) // 4


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculates the estimated cost of a single LLM call in USD."""
    config = MODEL_CONFIG.get(model, MODEL_CONFIG["gpt-4o-mini"])
    input_cost = (input_tokens / 1000) * config["cost_per_1k_input"]
    output_cost = (output_tokens / 1000) * config["cost_per_1k_output"]
    return round(input_cost + output_cost, 6)


# ─────────────────────────────────────────────
# REQUEST SCHEMA WITH BUILT-IN LIMITS
# ─────────────────────────────────────────────

class ControlledChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=5,
        # Hard limit on input — prevents prompt injection via massive inputs
        # Also controls cost: 4000 chars ≈ 1000 tokens ≈ $0.00015 for gpt-4o-mini
        max_length=4000,
    )
    model: Literal["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet"] = "gpt-4o-mini"

    max_tokens: int = Field(
        default=500,
        ge=1,
        # Hard cap on output — most answers don't need more than 1000 tokens
        # Prevents runaway costs from long responses
        le=2000,
    )

    # User tier — in real apps, this comes from the JWT token (not the request body!)
    user_tier: Literal["free", "pro"] = "free"

    @field_validator("model")
    @classmethod
    def check_model_access(cls, model: str, info) -> str:
        """Ensure the user's tier allows access to the requested model."""
        user_tier = info.data.get("user_tier", "free")
        required_tier = MODEL_CONFIG.get(model, {}).get("tier_required", "pro")

        if required_tier == "pro" and user_tier == "free":
            raise ValueError(
                f"Model '{model}' requires a Pro subscription. "
                f"Please use 'gpt-4o-mini' on the free tier."
            )
        return model


# ─────────────────────────────────────────────
# DEMO ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/chat/controlled", tags=["Cost Control"])
async def controlled_chat(req: ControlledChatRequest):
    """
    A chat endpoint with full cost and latency controls:
    1. Model access gating (tier check)
    2. Input length limit (reduces cost + injection risk)
    3. Output token limit (controls response cost)
    4. Response caching (eliminates cost for repeated questions)
    5. Cost estimation (logged for monitoring)
    """
    # ── Step 1: Check cache ──────────────────────────────────────
    cache_key = get_cache_key(req.question, req.model)
    cached = get_from_cache(cache_key)
    if cached:
        cached["cache_hit"] = True
        return cached  # return immediately — zero LLM cost!

    # ── Step 2: Estimate cost before calling the LLM ────────────
    input_tokens = estimate_tokens(req.question)
    estimated_cost = estimate_cost(input_tokens, req.max_tokens, req.model)

    # ── Step 3: Call the LLM (simulated here) ───────────────────
    import asyncio
    await asyncio.sleep(0.5)  # simulate LLM call
    answer = f"Answer to '{req.question}' from {req.model}: This is the simulated response."

    output_tokens = estimate_tokens(answer)
    actual_cost = estimate_cost(input_tokens, output_tokens, req.model)

    # ── Step 4: Build response ───────────────────────────────────
    response = {
        "answer": answer,
        "model": req.model,
        "cache_hit": False,
        "metrics": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": actual_cost,
        },
    }

    # ── Step 5: Cache the response for future identical requests ─
    save_to_cache(cache_key, response)

    return response


@app.get("/cost/estimate", tags=["Cost Control"])
def estimate_cost_endpoint(
    input_text: str,
    max_output_tokens: int = 500,
    model: str = "gpt-4o-mini",
):
    """
    Returns the estimated cost before the user submits a request.
    Show this in your frontend so users understand the cost implications.
    """
    if model not in MODEL_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

    input_tokens = estimate_tokens(input_text)
    cost = estimate_cost(input_tokens, max_output_tokens, model)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "max_output_tokens": max_output_tokens,
        "estimated_cost_usd": cost,
        "note": "Token estimation is approximate (±20%). Actual cost may vary.",
    }


@app.get("/cost/models", tags=["Cost Control"])
def list_models():
    """Returns the pricing table for all supported models."""
    return {
        model: {
            "cost_per_1k_input_usd": config["cost_per_1k_input"],
            "cost_per_1k_output_usd": config["cost_per_1k_output"],
            "max_context_tokens": config["max_context"],
            "tier_required": config["tier_required"],
        }
        for model, config in MODEL_CONFIG.items()
    }
