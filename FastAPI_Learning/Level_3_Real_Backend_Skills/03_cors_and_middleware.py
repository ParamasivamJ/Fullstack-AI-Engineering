"""
Level 3 — CORS and Custom Middleware
======================================

CORS (Cross-Origin Resource Sharing) is the browser's security system.
Without it, your React frontend cannot talk to your FastAPI backend.

Custom Middleware wraps EVERY request — it runs before and after your route.
It is the right place for:
  - Request logging
  - Adding request IDs (for tracing)
  - Timing how long requests take
  - Enforcing global security headers

HOW TO RUN:
  uvicorn 03_cors_and_middleware:app --reload
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
import logging

# Configure Python's built-in logger
# In production, you would output JSON-structured logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Level 3: CORS and Middleware")


# ─────────────────────────────────────────────
# 1. CORS MIDDLEWARE
# ─────────────────────────────────────────────
# The browser blocks requests from one origin (e.g., localhost:3000)
# to a different origin (e.g., localhost:8000) UNLESS the server
# explicitly permits it in response headers.
#
# CORS middleware adds those permission headers automatically.

app.add_middleware(
    CORSMiddleware,
    # allow_origins lists which frontends can call this API.
    # NEVER use ["*"] in production — it allows any website to call your API.
    allow_origins=[
        "http://localhost:3000",     # local Next.js dev server
        "https://yourdomain.com",    # your production frontend
    ],
    # allow_credentials=True allows the browser to send cookies / auth headers
    allow_credentials=True,
    # allow_methods restricts which HTTP methods are permitted
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # allow_headers restricts which request headers are permitted
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    # expose_headers makes these response headers readable by the browser's JavaScript
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ─────────────────────────────────────────────
# 2. REQUEST LOGGING + TIMING MIDDLEWARE
# ─────────────────────────────────────────────
# BaseHTTPMiddleware gives you access to every request and response.
# The dispatch method is called for every single request.

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # ── BEFORE the route runs ──────────────────────────────────
        # Generate a unique ID for this specific request.
        # This lets you trace a request through all your logs.
        request_id = str(uuid.uuid4())[:8]  # Short ID: e.g., "a1b2c3d4"

        # Attach the request ID to the request state so route functions can read it
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            f"[{request_id}] → {request.method} {request.url.path}"
            f" | client: {request.client.host if request.client else 'unknown'}"
        )

        # ── CALL the actual route function ────────────────────────
        response: Response = await call_next(request)

        # ── AFTER the route runs ───────────────────────────────────
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[{request_id}] ← {response.status_code}"
            f" | {duration_ms:.2f}ms"
        )

        # Add custom headers to every response — useful for debugging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        return response


# Register the middleware — order matters!
# Middleware is applied in reverse order of registration (last added = outermost)
app.add_middleware(RequestLoggingMiddleware)


# ─────────────────────────────────────────────
# 3. SECURITY HEADERS MIDDLEWARE
# ─────────────────────────────────────────────
# These headers protect against common web attacks.
# Add them to every response automatically via middleware.

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevents browsers from guessing the Content-Type (MIME sniffing attack)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevents your site from being embedded in iframes (clickjacking attack)
        response.headers["X-Frame-Options"] = "DENY"

        # Forces browsers to use HTTPS for 1 year (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─────────────────────────────────────────────
# 4. DEMO ROUTES
# ─────────────────────────────────────────────

@app.get("/", tags=["Demo"])
def root():
    return {"message": "Check response headers for X-Request-ID and X-Process-Time"}


@app.get("/slow", tags=["Demo"])
async def slow_endpoint():
    """Simulates a slow operation so you can see the timing in headers."""
    import asyncio
    await asyncio.sleep(0.5)  # simulate 500ms latency
    return {"message": "Slow operation complete"}


@app.get("/request-info", tags=["Demo"])
def request_info(request: Request):
    """Shows how to read the request ID from route functions."""
    return {
        "request_id": request.state.request_id,
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown",
    }
