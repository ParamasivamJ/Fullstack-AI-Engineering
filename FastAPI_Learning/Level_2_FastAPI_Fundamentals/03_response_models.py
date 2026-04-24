"""
Level 2 — Response Models and Custom Responses
===============================================

Controlling your API's output is just as important as validating input.
This file teaches:
  - response_model: filter what fields are returned
  - status codes: communicate outcomes clearly
  - Union responses: different schemas for different outcomes
  - Custom response types: JSON, plain text, streaming

HOW TO RUN:
  uvicorn 03_response_models:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime

app = FastAPI(title="Level 2: Response Models")


# ─────────────────────────────────────────────
# SCHEMAS — input vs output separation
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TaskInDB(BaseModel):
    """Represents a task as it exists in the database (internal model)."""
    id: int
    title: str
    description: Optional[str]
    completed: bool
    owner_id: int
    created_at: datetime
    # This field should NEVER leave the server
    internal_score: float = 0.99

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    """What we actually return to the client — a filtered subset of TaskInDB."""
    id: int
    title: str
    description: Optional[str]
    completed: bool
    # Notice: owner_id, internal_score, created_at are intentionally excluded
    # The client does not need internal metadata

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    """Wrapper for paginated responses — always include total count in lists."""
    total: int
    page: int
    items: List[TaskOut]


class ErrorOut(BaseModel):
    """Consistent error response shape across the entire API."""
    detail: str
    code: str   # machine-readable error code for frontend handling


# ─────────────────────────────────────────────
# 1. response_model — automatic output filtering
# ─────────────────────────────────────────────

@app.post(
    "/tasks",
    # response_model tells FastAPI: "filter the return value through this schema"
    # Any field in TaskInDB that is NOT in TaskOut will be stripped before sending.
    # This is your first line of defense against leaking sensitive data.
    response_model=TaskOut,
    status_code=201,
    tags=["Tasks"],
)
def create_task(task: TaskCreate):
    # Simulating what a database would return — it includes internal fields
    db_task = TaskInDB(
        id=42,
        title=task.title,
        description=task.description,
        completed=False,
        owner_id=1,
        created_at=datetime.utcnow(),
        internal_score=0.87,   # ← this will be STRIPPED by response_model=TaskOut
    )
    # FastAPI filters db_task through TaskOut before sending the response.
    # The client will NEVER see owner_id or internal_score.
    return db_task


@app.get(
    "/tasks",
    response_model=TaskListOut,
    tags=["Tasks"],
)
def list_tasks(page: int = 1):
    # Always wrap lists in a pagination envelope.
    # Returning a bare list makes it impossible to add pagination later without breaking clients.
    fake_tasks = [
        TaskInDB(id=i, title=f"Task {i}", description=None,
                 completed=False, owner_id=1, created_at=datetime.utcnow(), internal_score=0.5)
        for i in range(1, 4)
    ]
    return TaskListOut(total=100, page=page, items=fake_tasks)  # type: ignore


# ─────────────────────────────────────────────
# 2. response_model_exclude_none — cleaner JSON output
# ─────────────────────────────────────────────

@app.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    # By default, None fields are included as null in JSON.
    # Setting this to True omits them entirely — cleaner for the frontend.
    response_model_exclude_none=True,
    tags=["Tasks"],
)
def get_task(task_id: int):
    return TaskInDB(
        id=task_id, title="Sample task", description=None,  # ← None field
        completed=False, owner_id=1, created_at=datetime.utcnow(), internal_score=0.5
    )
    # Response will be: {"id": 1, "title": "Sample task", "completed": false}
    # "description" is omitted because response_model_exclude_none=True


# ─────────────────────────────────────────────
# 3. Multiple response schemas (Union)
# ─────────────────────────────────────────────
# Sometimes a route can return different shapes depending on the outcome.
# Document this in the OpenAPI spec with responses dict.

@app.get(
    "/tasks/{task_id}/detail",
    # You can't use Union directly in response_model cleanly — use responses instead
    responses={
        200: {"model": TaskOut, "description": "Task found and returned"},
        404: {"model": ErrorOut, "description": "Task not found"},
    },
    tags=["Tasks"],
)
def get_task_detail(task_id: int):
    if task_id > 100:
        # Return a JSONResponse directly when you need custom status codes
        return JSONResponse(
            status_code=404,
            content={"detail": "Task not found", "code": "TASK_NOT_FOUND"},
        )
    return TaskOut(id=task_id, title="Found task", description="Here it is", completed=False)


# ─────────────────────────────────────────────
# 4. Custom Response Classes
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    # PlainTextResponse is faster than JSONResponse for simple strings
    # Health check endpoints are called frequently by load balancers — keep them light
    return PlainTextResponse("OK", status_code=200)


@app.delete(
    "/tasks/{task_id}",
    # status_code=204 means "No Content" — success but nothing to return.
    # The client should update its UI based on the status code alone.
    status_code=204,
    # response_class=Response means FastAPI will not serialize anything
    response_class=Response,
    tags=["Tasks"],
)
def delete_task(task_id: int):
    # Perform the delete...
    # Return None or an empty Response — do NOT return a body with 204
    return Response(status_code=204)


# ─────────────────────────────────────────────
# 5. Adding metadata to the OpenAPI docs
# ─────────────────────────────────────────────

@app.get(
    "/tasks/{task_id}/export",
    tags=["Tasks"],
    summary="Export task as plain text",
    description="""
    Returns the task formatted as plain text for copying into a document.
    Use the `/tasks/{task_id}` endpoint if you need structured JSON.
    """,
    # deprecated=True shows a warning in Swagger UI — useful for API versioning
    deprecated=False,
    response_class=PlainTextResponse,
)
def export_task(task_id: int):
    return PlainTextResponse(
        f"Task #{task_id}\nTitle: Sample Task\nStatus: In Progress\n",
        status_code=200,
    )
