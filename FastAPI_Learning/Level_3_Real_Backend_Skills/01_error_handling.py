"""
Level 3 — Error Handling (Expert Level)
========================================

Default FastAPI errors are generic and hard for frontends to handle.
Expert-level error handling means:
  1. Consistent error shape across the entire API
  2. Machine-readable error codes (not just human messages)
  3. Custom exception classes that carry context
  4. Global exception handlers that catch everything

HOW TO RUN:
  uvicorn 01_error_handling:app --reload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI(title="Level 3: Error Handling")


# ─────────────────────────────────────────────
# 1. CONSISTENT ERROR SCHEMA
# ─────────────────────────────────────────────
# Every error your API returns should look the same.
# The frontend should never have to guess the shape of an error.

class APIError(BaseModel):
    """Standard error response shape for the entire API."""
    # Human-readable message for displaying in UI
    detail: str
    # Machine-readable code — frontend can switch on this to show specific UI
    code: str
    # Optional extra context (field name, request ID, etc.)
    context: Optional[dict] = None


# ─────────────────────────────────────────────
# 2. CUSTOM EXCEPTION CLASSES
# ─────────────────────────────────────────────
# Instead of raising HTTPException(status_code=404) everywhere,
# create domain-specific exceptions with meaningful names.
# This makes your codebase self-documenting.

class TaskNotFoundError(Exception):
    """Raised when a task cannot be found in the database."""
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class InsufficientPermissionError(Exception):
    """Raised when a user tries to access a resource they do not own."""
    def __init__(self, user_id: int, resource: str):
        self.user_id = user_id
        self.resource = resource
        super().__init__(f"User {user_id} cannot access {resource}")


class LLMQuotaExceededError(Exception):
    """Raised when a user exceeds their monthly AI usage quota."""
    def __init__(self, user_id: int, limit: int):
        self.user_id = user_id
        self.limit = limit


# ─────────────────────────────────────────────
# 3. GLOBAL EXCEPTION HANDLERS
# ─────────────────────────────────────────────
# @app.exception_handler registers a function to run whenever a specific
# exception type is raised ANYWHERE in the application.
# This keeps error formatting in ONE place instead of scattered everywhere.

@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    # request gives you access to URL, headers, etc. for logging
    return JSONResponse(
        status_code=404,
        content=APIError(
            detail=f"Task with ID {exc.task_id} does not exist",
            code="TASK_NOT_FOUND",
            context={"task_id": exc.task_id},
        ).model_dump(),
    )


@app.exception_handler(InsufficientPermissionError)
async def permission_handler(request: Request, exc: InsufficientPermissionError):
    return JSONResponse(
        status_code=403,
        content=APIError(
            detail="You do not have permission to access this resource",
            code="FORBIDDEN",
            context={"resource": exc.resource},
        ).model_dump(),
    )


@app.exception_handler(LLMQuotaExceededError)
async def quota_handler(request: Request, exc: LLMQuotaExceededError):
    return JSONResponse(
        status_code=429,
        content=APIError(
            detail=f"Monthly AI usage limit of {exc.limit} requests exceeded",
            code="QUOTA_EXCEEDED",
            context={"user_id": exc.user_id, "monthly_limit": exc.limit},
        ).model_dump(),
    )


# ─────────────────────────────────────────────
# 4. OVERRIDE FASTAPI'S DEFAULT VALIDATION ERROR
# ─────────────────────────────────────────────
# By default, FastAPI returns validation errors in its own format.
# Override this to match your APIError schema so the frontend always
# handles one consistent error shape.

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # exc.errors() returns a list of all validation failures
    # We pick the first one for the main error message
    errors = exc.errors()
    first_error = errors[0] if errors else {}

    # The "loc" tuple tells you which field failed: ("body", "title") means body.title
    field_path = " → ".join(str(loc) for loc in first_error.get("loc", []))

    return JSONResponse(
        status_code=422,
        content=APIError(
            detail=first_error.get("msg", "Validation failed"),
            code="VALIDATION_ERROR",
            context={
                "field": field_path,
                "all_errors": errors,  # include all errors for the frontend to highlight multiple fields
            },
        ).model_dump(),
    )


# ─────────────────────────────────────────────
# 5. CATCH-ALL HANDLER (safety net)
# ─────────────────────────────────────────────
# This catches any exception you did NOT handle explicitly.
# Without this, an unexpected crash returns a raw HTML 500 error
# which leaks your stack trace to the client — a security risk.

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # In production: log the full traceback here using your logging system
    # But return only a generic message to the client
    print(f"UNHANDLED EXCEPTION: {type(exc).__name__}: {exc}")  # replace with proper logging
    return JSONResponse(
        status_code=500,
        content=APIError(
            detail="An unexpected error occurred. Our team has been notified.",
            code="INTERNAL_ERROR",
        ).model_dump(),
    )


# ─────────────────────────────────────────────
# 6. DEMO ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/tasks/{task_id}", tags=["Demo"])
def get_task(task_id: int, user_id: int = 1):
    if task_id == 0:
        # Raise your custom exception — the handler above catches it
        raise TaskNotFoundError(task_id=task_id)

    if task_id > 100:
        raise InsufficientPermissionError(user_id=user_id, resource=f"task/{task_id}")

    return {"id": task_id, "title": "Sample task"}


@app.post("/ai/chat", tags=["Demo"])
def ai_chat(user_id: int = 1):
    # Simulate quota check before calling the LLM
    simulated_usage = 1001
    monthly_limit = 1000
    if simulated_usage > monthly_limit:
        raise LLMQuotaExceededError(user_id=user_id, limit=monthly_limit)

    return {"response": "Hello from the AI!"}


@app.get("/crash", tags=["Demo"])
def trigger_crash():
    # This simulates an unexpected error — the catch-all handler responds safely
    raise RuntimeError("Something totally unexpected happened in a library")
