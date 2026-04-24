"""
Level 5 — Multi-User Design (Tenant Isolation)
================================================

In a multi-user AI app, the most critical security property is:
  User A can NEVER see, modify, or delete User B's data.

This is called "tenant isolation" and it must be enforced at EVERY layer:
  1. Database queries (always filter by owner_id)
  2. API routes (validate ownership before returning or modifying)
  3. Background tasks (scope work to the correct user)
  4. Vector DB search (filter by user namespace)

This is one of the most common production security bugs in AI apps.
One missing WHERE clause and you have a data leak.

HOW TO RUN:
  uvicorn 06_multi_user_design:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime

app = FastAPI(title="Level 5: Multi-User Design")


# ─────────────────────────────────────────────
# FAKE DATA STORE (replace with PostgreSQL in production)
# ─────────────────────────────────────────────

class UserRecord(BaseModel):
    id: str
    username: str
    token: str  # simplified — in real apps this is a JWT

class TaskRecord(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: str

# Simulated multi-user database
USERS: dict[str, UserRecord] = {
    "token-alice": UserRecord(id="user-1", username="alice", token="token-alice"),
    "token-bob":   UserRecord(id="user-2", username="bob",   token="token-bob"),
}
TASKS: dict[str, TaskRecord] = {}


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class TaskOut(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: str


# ─────────────────────────────────────────────
# AUTH DEPENDENCY
# ─────────────────────────────────────────────

def get_current_user(token: str = "") -> UserRecord:
    """Simulates JWT auth — looks up user by token."""
    user = USERS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# ─────────────────────────────────────────────
# OWNERSHIP VERIFICATION PATTERN
# ─────────────────────────────────────────────

def get_owned_task(task_id: str, current_user: UserRecord = Depends(get_current_user)) -> TaskRecord:
    """
    This dependency pattern is the core of tenant isolation.
    It:
      1. Fetches the task by ID
      2. Verifies the current user OWNS it
      3. Only then returns it to the route function

    By using this as a dependency, you can never accidentally
    forget the ownership check in a route function.
    """
    task = TASKS.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # THE CRITICAL CHECK — never skip this
    if task.owner_id != current_user.id:
        # Return 404, not 403 — this is a security best practice.
        # Returning 403 tells the attacker the resource EXISTS.
        # Returning 404 gives no information.
        raise HTTPException(status_code=404, detail="Task not found")

    return task


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.post("/tasks", response_model=TaskOut, status_code=201, tags=["Tasks"])
def create_task(
    task: TaskCreate,
    current_user: UserRecord = Depends(get_current_user),
):
    task_id = str(uuid4())
    new_task = TaskRecord(
        id=task_id,
        title=task.title,
        owner_id=current_user.id,  # ← always set owner to CURRENT user, never from request body
        created_at=datetime.utcnow().isoformat(),
    )
    TASKS[task_id] = new_task
    return TaskOut(**new_task.model_dump())


@app.get("/tasks", response_model=list[TaskOut], tags=["Tasks"])
def list_tasks(current_user: UserRecord = Depends(get_current_user)):
    """
    Returns ONLY the current user's tasks.
    The filter `task.owner_id == current_user.id` is the tenant isolation clause.
    In SQL: WHERE owner_id = :current_user_id
    """
    user_tasks = [
        TaskOut(**task.model_dump())
        for task in TASKS.values()
        if task.owner_id == current_user.id  # ← TENANT ISOLATION CLAUSE
    ]
    return user_tasks


@app.get("/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"])
def get_task(
    # get_owned_task handles both "does it exist?" AND "does current user own it?"
    task: TaskRecord = Depends(get_owned_task),
):
    return TaskOut(**task.model_dump())


@app.delete("/tasks/{task_id}", status_code=204, tags=["Tasks"])
def delete_task(
    task: TaskRecord = Depends(get_owned_task),
):
    """Deletes a task only if the current user owns it."""
    del TASKS[task.id]


# ─────────────────────────────────────────────
# DEMO: showing isolation in action
# ─────────────────────────────────────────────

@app.post("/demo/setup", tags=["Demo"])
def setup_demo():
    """Creates tasks for both alice and bob so you can test isolation."""
    alice = USERS["token-alice"]
    bob = USERS["token-bob"]

    # Alice's tasks
    for title in ["Alice's task 1", "Alice's task 2"]:
        tid = str(uuid4())
        TASKS[tid] = TaskRecord(id=tid, title=title, owner_id=alice.id, created_at=datetime.utcnow().isoformat())

    # Bob's tasks
    for title in ["Bob's task 1"]:
        tid = str(uuid4())
        TASKS[tid] = TaskRecord(id=tid, title=title, owner_id=bob.id, created_at=datetime.utcnow().isoformat())

    return {
        "setup": "complete",
        "alice_token": "token-alice",
        "bob_token": "token-bob",
        "instruction": "Call GET /tasks?token=token-alice vs GET /tasks?token=token-bob and compare results",
    }


# ─────────────────────────────────────────────
# VECTOR DB TENANT ISOLATION (pattern note)
# ─────────────────────────────────────────────
# When using pgvector or Qdrant, you must also scope vector search to the user.
#
# pgvector (SQL filter):
#   SELECT * FROM chunks
#   JOIN documents ON chunks.document_id = documents.id
#   WHERE documents.owner_id = :current_user_id  ← tenant filter
#   ORDER BY embedding <=> :query_vector
#   LIMIT 5;
#
# Qdrant (filter in search):
#   client.search(
#     collection_name="docs",
#     query_vector=embedding,
#     query_filter=Filter(must=[FieldCondition(key="owner_id", match=MatchValue(value=user_id))]),
#     limit=5,
#   )
#
# Without these filters, every user can search every other user's documents.
# This is a critical privacy and compliance issue.
