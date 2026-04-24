"""
Level 5 — Structured Logging with Request IDs
==============================================

Logging in AI apps is not optional — it is how you:
  - Debug production issues without reproducing them locally
  - Track LLM usage and cost per user
  - Monitor latency trends
  - Build an audit trail for compliance

Expert logging means:
  - JSON-structured logs (parseable by tools like Datadog, Grafana)
  - Every log line has a request_id to trace a full request
  - Different log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - Sensitive data is NEVER logged (passwords, tokens, PII)

HOW TO RUN:
  uvicorn 02_logging_structured:app --reload
"""

from fastapi import FastAPI, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import json
import time
import uuid
import sys
from typing import Any


# ─────────────────────────────────────────────
# 1. JSON FORMATTER
# ─────────────────────────────────────────────
# Plain text logs are hard to search and filter.
# JSON logs are structured — log tools can filter by field.

class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines instead of plain text."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields if the caller passed them via extra={}
        for key, val in record.__dict__.items():
            if key not in ("msg", "args", "levelname", "name", "pathname",
                           "filename", "module", "lineno", "funcName",
                           "created", "msecs", "relativeCreated", "thread",
                           "threadName", "processName", "process", "message",
                           "exc_info", "exc_text", "stack_info", "levelno"):
                log_entry[key] = val

        # Append exception info if there is one
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name: str) -> logging.Logger:
    """Creates and configures a named logger with JSON output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove any default handlers (avoid duplicate logs)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Prevent log records from propagating to the root logger
    logger.propagate = False

    return logger


# One logger per module — this is the standard Python pattern
logger = setup_logger("api")


# ─────────────────────────────────────────────
# 2. REQUEST LOGGING MIDDLEWARE
# ─────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attaches a unique request ID to every request for end-to-end tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a short request ID (use UUID in production)
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
            },
        )

        response = await call_next(request)

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response


# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(title="Level 5: Structured Logging")
app.add_middleware(RequestIDMiddleware)


# ─────────────────────────────────────────────
# 3. LOGGING AI CALLS
# ─────────────────────────────────────────────
# Every LLM call should be logged with cost-tracking fields.
# This builds the data you need to analyze usage and control costs.

import asyncio

async def call_llm_with_logging(
    prompt: str,
    model: str,
    user_id: str,
    request_id: str,
) -> str:
    """Wraps an LLM call with structured logging for observability."""
    input_tokens = len(prompt) // 4  # rough estimate
    start = time.perf_counter()

    logger.info(
        "LLM call started",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "model": model,
            "input_tokens": input_tokens,
        },
    )

    try:
        # In production: replace with real LLM call
        await asyncio.sleep(0.5)
        response_text = f"Response to: {prompt[:50]}..."

        duration = (time.perf_counter() - start) * 1000
        output_tokens = len(response_text) // 4

        logger.info(
            "LLM call completed",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": round(duration, 2),
                # In real apps: calculate from actual token counts
                "estimated_cost_usd": round((input_tokens + output_tokens) / 1000 * 0.0006, 6),
            },
        )
        return response_text

    except Exception as e:
        logger.error(
            "LLM call failed",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "model": model,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,  # includes the full stack trace in the log
        )
        raise


# ─────────────────────────────────────────────
# 4. DEMO ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/chat", tags=["Demo"])
async def chat(request: Request, message: str, user_id: str = "user_1"):
    # Read request_id from state (set by middleware)
    request_id = request.state.request_id

    # NEVER log the full message in production if it may contain PII
    logger.info(
        "Chat request received",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "message_length": len(message),  # log length, not content
        },
    )

    response = await call_llm_with_logging(
        prompt=message,
        model="gpt-4o-mini",
        user_id=user_id,
        request_id=request_id,
    )

    return {"response": response, "request_id": request_id}


@app.get("/health", tags=["System"])
def health(request: Request):
    logger.debug(
        "Health check",
        extra={"request_id": getattr(request.state, "request_id", "none")},
    )
    return {"status": "ok"}
