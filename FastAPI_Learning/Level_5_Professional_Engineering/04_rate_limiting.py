"""
Level 5 — Rate Limiting
========================

Rate limiting prevents:
  - Abuse (one user sending 10,000 requests/minute)
  - Runaway LLM costs (bot hammering your AI endpoints)
  - DDoS attacks (overwhelming your server)
  - Accidental client bugs (infinite retry loops)

Two approaches:
  1. slowapi — the standard FastAPI rate limiter (works like Flask-Limiter)
  2. Custom middleware with an in-memory counter (for learning/no-Redis setup)

HOW TO RUN:
  pip install slowapi
  uvicorn 04_rate_limiting:app --reload

  Then run this in a terminal to see 429 errors:
  for i in {1..15}; do curl -s http://localhost:8000/test | python -m json.tool; done
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from collections import defaultdict


# ─────────────────────────────────────────────
# APPROACH 1: Custom in-memory rate limiter
# ─────────────────────────────────────────────
# This is easy to understand and requires no external dependencies.
# Limitation: it is per-process only (does not work in multi-instance deployments).
# In production: use Redis + slowapi or a reverse proxy like nginx.

class InMemoryRateLimiter:
    """
    Sliding window rate limiter.
    Tracks how many requests a key (IP or user_id) made in the last N seconds.
    """

    def __init__(self):
        # key → list of timestamps of recent requests
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Returns (is_allowed, remaining_requests).
        Cleans up old timestamps outside the window.
        """
        now = time.time()
        window_start = now - window_seconds

        # Remove timestamps older than the window
        self._requests[key] = [
            ts for ts in self._requests[key]
            if ts > window_start
        ]

        current_count = len(self._requests[key])

        if current_count >= limit:
            return False, 0

        # Record this request
        self._requests[key].append(now)
        remaining = limit - current_count - 1
        return True, remaining


# Global rate limiter instance (shared across all requests)
limiter = InMemoryRateLimiter()


# ─────────────────────────────────────────────
# RATE LIMIT DEPENDENCY (per-route control)
# ─────────────────────────────────────────────
# Using a dependency lets you apply different limits to different routes.
# AI endpoints get stricter limits than normal endpoints.

def rate_limit(limit: int = 60, window: int = 60):
    """
    Returns a dependency that enforces a rate limit.

    Usage:
      @app.post("/chat", dependencies=[Depends(rate_limit(limit=10, window=60))])
      # This route allows max 10 requests per 60 seconds per IP
    """
    def _check(request: Request):
        # Use IP address as the key — in production, use user_id after auth
        client_ip = request.client.host if request.client else "unknown"
        allowed, remaining = limiter.is_allowed(client_ip, limit, window)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {limit} requests per {window} seconds.",
                headers={
                    # These headers tell the client when they can retry
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Pass rate limit info to response headers via request state
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit

    return _check


# ─────────────────────────────────────────────
# RATE LIMIT HEADER MIDDLEWARE
# ─────────────────────────────────────────────
# Adds rate limit headers to every response so clients know their status.

class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Add rate limit info to headers if set by the dependency
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)

        return response


# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(title="Level 5: Rate Limiting")
app.add_middleware(RateLimitHeadersMiddleware)


# ─────────────────────────────────────────────
# DEMO ROUTES WITH DIFFERENT RATE LIMITS
# ─────────────────────────────────────────────

# Standard endpoint: 60 requests per minute per IP
@app.get(
    "/test",
    tags=["Rate Limiting"],
    dependencies=[Depends(rate_limit(limit=10, window=60))],  # 10/min for demo
    summary="Standard endpoint — 10 requests/minute",
)
def test_endpoint(request: Request):
    return {
        "message": "Request succeeded",
        "rate_limit_remaining": getattr(request.state, "rate_limit_remaining", "N/A"),
    }


# AI endpoint: much stricter — 5 requests per minute
@app.post(
    "/ai/chat",
    tags=["Rate Limiting"],
    dependencies=[Depends(rate_limit(limit=5, window=60))],
    summary="AI endpoint — strictly limited to 5 requests/minute",
)
def ai_chat(request: Request, message: str = "Hello"):
    return {
        "response": f"AI answer to: {message}",
        "note": "This endpoint is strictly rate-limited to prevent cost abuse",
    }


# Public endpoint: no rate limit
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────
# APPROACH 2: PER-USER RATE LIMIT (production)
# ─────────────────────────────────────────────
# After the user authenticates, use their user_id as the rate limit key.
# This is fairer than IP-based limiting (multiple users can share one IP).

class FakeCurrentUser:
    id: str = "user_123"


def get_user_rate_limit(limit: int = 100, window: int = 60):
    """Rate limit by authenticated user ID instead of IP."""
    def _check(request: Request, user: FakeCurrentUser = Depends()):
        allowed, remaining = limiter.is_allowed(
            key=f"user:{user.id}",  # user-scoped key, not IP-scoped
            limit=limit,
            window=window,
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"You've exceeded your limit of {limit} requests per {window}s",
                headers={"Retry-After": str(window)},
            )
        request.state.rate_limit_remaining = remaining
    return _check
