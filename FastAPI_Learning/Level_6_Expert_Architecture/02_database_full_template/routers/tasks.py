"""
Level 6 — Routers: Tasks
=========================
Production-pattern router for task management.
Demonstrates: pagination, ownership dependency, partial update (PATCH).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime

router = APIRouter()


# ─── Simplified schemas ──────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: int = Field(default=1, ge=1, le=5)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)

class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    completed: bool
    priority: int
    owner_id: str
    created_at: str

class TaskListOut(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[TaskOut]


# ─── Fake data store ─────────────────────────────────────────────────────

_tasks: dict[str, dict] = {}


def _get_user_or_401(token: str) -> str:
    """Simulates auth dependency — returns user_id."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return f"user_{token}"  # in production: decode JWT → user.id


def _get_owned_task_or_404(task_id: str, user_id: str) -> dict:
    """
    Fetches a task and verifies ownership.
    This is the tenant isolation enforcement point for task routes.
    """
    task = _tasks.get(task_id)
    if not task or task["owner_id"] != user_id:
        # Always 404 — never reveal a resource exists if user doesn't own it
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ─── Routes ──────────────────────────────────────────────────────────────

@router.post("/", response_model=TaskOut, status_code=201,
             summary="Create a new task")
def create_task(task: TaskCreate, token: str = ""):
    user_id = _get_user_or_401(token)
    task_id = str(uuid4())
    record = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "completed": False,
        "priority": task.priority,
        "owner_id": user_id,     # ← always from the JWT, never from the request body
        "created_at": datetime.utcnow().isoformat(),
    }
    _tasks[task_id] = record
    return TaskOut(**record)


@router.get("/", response_model=TaskListOut, summary="List current user's tasks")
def list_tasks(
    token: str = "",
    completed: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    user_id = _get_user_or_401(token)

    # Tenant isolation: only this user's tasks
    user_tasks = [t for t in _tasks.values() if t["owner_id"] == user_id]

    # Optional filter
    if completed is not None:
        user_tasks = [t for t in user_tasks if t["completed"] == completed]

    total = len(user_tasks)
    # Paginate
    start = (page - 1) * per_page
    page_items = [TaskOut(**t) for t in user_tasks[start: start + per_page]]

    return TaskListOut(total=total, page=page, per_page=per_page, items=page_items)


@router.get("/{task_id}", response_model=TaskOut, summary="Get a specific task")
def get_task(task_id: str, token: str = ""):
    user_id = _get_user_or_401(token)
    task = _get_owned_task_or_404(task_id, user_id)
    return TaskOut(**task)


@router.patch("/{task_id}", response_model=TaskOut, summary="Partially update a task")
def update_task(task_id: str, updates: TaskUpdate, token: str = ""):
    user_id = _get_user_or_401(token)
    task = _get_owned_task_or_404(task_id, user_id)

    # Only apply fields that were actually sent (not None)
    patch = updates.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    task.update(patch)
    return TaskOut(**task)


@router.delete("/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: str, token: str = ""):
    user_id = _get_user_or_401(token)
    _get_owned_task_or_404(task_id, user_id)  # validates ownership
    del _tasks[task_id]
    # 204 No Content — return nothing
