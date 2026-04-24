"""
Level 6 — API Versioning
==========================

APIs evolve. Clients (mobile apps, other services) can't always update immediately.
Versioning lets you change your API without breaking existing clients.

Strategies:
  1. URL versioning:    /v1/tasks, /v2/tasks  ← most common, explicit, recommended
  2. Header versioning: API-Version: v2       ← cleaner URLs but harder to test
  3. Query param:       /tasks?version=2      ← avoid — pollutes query strings

This file demonstrates URL versioning with FastAPI routers.

HOW TO RUN:
  uvicorn 06_api_versioning:app --reload
  Test:
    GET http://localhost:8000/v1/tasks  → old response format
    GET http://localhost:8000/v2/tasks  → new response format
"""

from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="Level 6: API Versioning",
    description="Demonstrates how to run v1 and v2 of an API simultaneously",
)


# ─────────────────────────────────────────────
# V1 SCHEMAS (old format — must not change)
# ─────────────────────────────────────────────
# Once v1 is live and clients depend on it, NEVER change the schema.
# Any new fields or format changes go into v2.

class TaskOutV1(BaseModel):
    """V1 task response — simple flat structure."""
    id: int
    title: str
    done: bool          # v1 used "done" instead of "completed"
    owner: str          # v1 returned username as a string


# ─────────────────────────────────────────────
# V2 SCHEMAS (new improved format)
# ─────────────────────────────────────────────

class TaskOwnerV2(BaseModel):
    """V2 returns owner as a nested object (richer data)."""
    id: int
    username: str

class TaskOutV2(BaseModel):
    """V2 task response — improved structure with more fields."""
    id: int
    title: str
    description: Optional[str]
    completed: bool         # renamed from "done" for clarity
    priority: int           # new field in v2
    owner: TaskOwnerV2      # nested object instead of plain string
    created_at: datetime    # new field in v2


class TaskListV2(BaseModel):
    """V2 adds pagination envelope (v1 returned a bare list)."""
    total: int
    page: int
    items: list[TaskOutV2]


# ─────────────────────────────────────────────
# V1 ROUTER
# ─────────────────────────────────────────────

router_v1 = APIRouter(prefix="/v1", tags=["v1 (Legacy — do not use for new projects)"])


@router_v1.get("/tasks", response_model=list[TaskOutV1])
def list_tasks_v1():
    """V1: Returns a bare list of tasks with flat owner string."""
    return [
        TaskOutV1(id=1, title="Write tests", done=False, owner="alice"),
        TaskOutV1(id=2, title="Deploy app", done=True, owner="alice"),
    ]


@router_v1.get("/tasks/{task_id}", response_model=TaskOutV1)
def get_task_v1(task_id: int):
    return TaskOutV1(id=task_id, title="Sample task", done=False, owner="alice")


# ─────────────────────────────────────────────
# V2 ROUTER
# ─────────────────────────────────────────────

router_v2 = APIRouter(prefix="/v2", tags=["v2 (Current — use this)"])


@router_v2.get("/tasks", response_model=TaskListV2)
def list_tasks_v2(page: int = 1):
    """V2: Returns paginated tasks with nested owner and priority."""
    owner = TaskOwnerV2(id=1, username="alice")
    tasks = [
        TaskOutV2(
            id=i,
            title=f"Task {i}",
            description=f"Description for task {i}",
            completed=i % 2 == 0,
            priority=i % 5 + 1,
            owner=owner,
            created_at=datetime.utcnow(),
        )
        for i in range(1, 4)
    ]
    return TaskListV2(total=100, page=page, items=tasks)


@router_v2.get("/tasks/{task_id}", response_model=TaskOutV2)
def get_task_v2(task_id: int):
    return TaskOutV2(
        id=task_id,
        title="Sample task",
        description="Rich description with context",
        completed=False,
        priority=3,
        owner=TaskOwnerV2(id=1, username="alice"),
        created_at=datetime.utcnow(),
    )


# ─────────────────────────────────────────────
# DEPRECATION HEADER MIDDLEWARE
# ─────────────────────────────────────────────
# Best practice: warn v1 clients that they should upgrade.

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class DeprecationWarningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/v1"):
            # This header is a convention that tells API clients to upgrade
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2026-12-31"  # when v1 will be removed
            response.headers["Link"] = '</v2/tasks>; rel="successor-version"'
        return response


app.add_middleware(DeprecationWarningMiddleware)
app.include_router(router_v1)
app.include_router(router_v2)


# ─────────────────────────────────────────────
# VERSIONING STRATEGY NOTES
# ─────────────────────────────────────────────
# When to version:
#   ✅ Removing a field
#   ✅ Renaming a field
#   ✅ Changing a field type (e.g., owner: str → owner: {id, username})
#   ✅ Changing response structure (list → paginated envelope)
#
# When NOT to version:
#   ✅ Adding a new OPTIONAL field (backward-compatible — no version needed)
#   ✅ Adding a new endpoint (no existing clients are affected)
#   ✅ Bug fixes that make behavior match the documented spec

@app.get("/", tags=["Info"])
def api_info():
    return {
        "versions": {
            "v1": {
                "status": "deprecated",
                "sunset": "2026-12-31",
                "docs": "/docs#tag/v1",
            },
            "v2": {
                "status": "current",
                "docs": "/docs#tag/v2",
            },
        },
        "recommendation": "Use v2 for all new development",
    }
