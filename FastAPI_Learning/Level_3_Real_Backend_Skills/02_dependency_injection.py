"""
Level 3 — Dependency Injection (The Most Important FastAPI Concept)
====================================================================

Dependency Injection (DI) is FastAPI's most powerful feature.
It lets you define reusable logic ONCE and inject it into any route.

Uses:
  - Opening / closing database sessions
  - Authenticating users from a JWT token
  - Checking permissions
  - Logging requests
  - Rate limiting
  - Feature flags

Without DI: copy-paste the same auth code into every route (messy, error-prone)
With DI:    write auth once, inject it wherever you need it (clean, testable)

HOW TO RUN:
  uvicorn 02_dependency_injection:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional, Annotated
import time

app = FastAPI(title="Level 3: Dependency Injection")


# ─────────────────────────────────────────────
# 1. SIMPLEST DEPENDENCY — a plain function
# ─────────────────────────────────────────────
# Any Python function can be a dependency.
# FastAPI calls it automatically before your route function runs.

def get_current_timestamp() -> float:
    """Returns the current UNIX timestamp. Injected as a dependency."""
    return time.time()


@app.get("/time", tags=["Simple DI"])
def get_time(
    # Depends(get_current_timestamp) tells FastAPI:
    # "Call get_current_timestamp() and pass its return value as 'ts'"
    ts: float = Depends(get_current_timestamp),
):
    return {"timestamp": ts}


# ─────────────────────────────────────────────
# 2. DATABASE SESSION DEPENDENCY (the pattern you will use in every project)
# ─────────────────────────────────────────────
# In real apps this would use SQLAlchemy.
# Here we use a fake session class to show the pattern.

class FakeDBSession:
    """Simulates a database session object."""
    def __init__(self):
        self.is_open = True
        print("DB: session OPENED")  # In real apps, this connects to PostgreSQL

    def close(self):
        self.is_open = False
        print("DB: session CLOSED")  # Always closes after the request finishes

    def query(self, model: str):
        return f"Result from {model}"


def get_db():
    """
    Yields a database session for the duration of one request.
    The 'yield' is critical — code AFTER yield runs as cleanup after the request.
    This guarantees the session is ALWAYS closed, even if an exception occurs.
    """
    db = FakeDBSession()
    try:
        # Everything before yield runs BEFORE the route function
        yield db  # ← the session is passed to the route function
        # Everything after yield runs AFTER the route function
    finally:
        # 'finally' ensures this runs even if the route raised an exception
        db.close()


@app.get("/tasks", tags=["Database DI"])
def get_tasks(
    # The db session is opened, passed here, and closed automatically after
    db: FakeDBSession = Depends(get_db),
):
    result = db.query("Task")
    return {"data": result, "session_open": db.is_open}  # session_open will be True here


# ─────────────────────────────────────────────
# 3. AUTH DEPENDENCY — extracting a user from a JWT
# ─────────────────────────────────────────────
# In real apps, you decode a JWT. Here we use a simple API key in a header.

class CurrentUser(BaseModel):
    id: int
    username: str
    role: str


# Fake "database" of API keys
FAKE_API_KEYS = {
    "admin-key-123": CurrentUser(id=1, username="admin", role="admin"),
    "user-key-456": CurrentUser(id=2, username="alice", role="user"),
}


def get_current_user(
    # Header() extracts a value from HTTP request headers.
    # 'x_api_key' maps to the 'X-API-Key' header (FastAPI auto-converts underscores to hyphens)
    x_api_key: str = Header(..., description="Your API key"),
) -> CurrentUser:
    """
    Validates the API key and returns the current user.
    Raising HTTPException here cancels the request — the route function never runs.
    """
    user = FAKE_API_KEYS.get(x_api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return user


@app.get("/profile", tags=["Auth DI"])
def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
):
    # At this point, we KNOW current_user is valid — get_current_user enforced it
    return {"user": current_user.model_dump()}


# ─────────────────────────────────────────────
# 4. PERMISSION DEPENDENCY — building on auth
# ─────────────────────────────────────────────
# Dependencies can call other dependencies.
# This creates a "dependency chain": get_db + get_current_user + require_admin

def require_admin(
    # This dependency itself depends on get_current_user — DI chains automatically
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Only admin users can access routes that depend on this."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@app.delete("/tasks/{task_id}", tags=["Auth DI"])
def delete_task(
    task_id: int,
    # If the user is not admin, the HTTPException from require_admin fires here
    admin: CurrentUser = Depends(require_admin),
    db: FakeDBSession = Depends(get_db),
):
    return {"deleted": task_id, "by": admin.username}


# ─────────────────────────────────────────────
# 5. ANNOTATED SHORTHAND (modern Python style)
# ─────────────────────────────────────────────
# Annotated is the clean, modern way to express dependencies.
# Avoids repeating Depends(get_current_user) everywhere.

# Define type aliases once
DB = Annotated[FakeDBSession, Depends(get_db)]
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_admin)]


@app.post("/tasks", tags=["Annotated DI"], status_code=201)
def create_task(
    title: str,
    db: DB,           # ← same as: db: FakeDBSession = Depends(get_db)
    user: AuthUser,   # ← same as: user: CurrentUser = Depends(get_current_user)
):
    return {"task": title, "created_by": user.username}


@app.get("/admin/users", tags=["Annotated DI"])
def list_all_users(
    admin: AdminUser,  # ← automatically enforces admin role
    db: DB,
):
    return {"users": ["alice", "bob"], "requested_by": admin.username}
