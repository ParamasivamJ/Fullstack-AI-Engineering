"""
Level 2 — Routes and Parameters
================================

This file teaches the three ways to pass data into a FastAPI endpoint:
  1. Path parameters   → embedded in the URL path (e.g., /users/{user_id})
  2. Query parameters  → appended to the URL (e.g., /tasks?limit=10&page=2)
  3. Request body      → JSON sent in the HTTP body (POST/PUT/PATCH only)

HOW TO RUN:
  uvicorn 01_routes_and_params:app --reload
  Then open: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Path, Query, Body
from pydantic import BaseModel, Field
from typing import Optional

# ─────────────────────────────────────────────
# 1. CREATE THE APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="Level 2: Routes and Parameters",
    description="Learn path params, query params, and request bodies",
    version="1.0.0",
    # docs_url sets the path for the auto-generated Swagger UI
    docs_url="/docs",
)


# ─────────────────────────────────────────────
# 2. PATH PARAMETERS
# ─────────────────────────────────────────────
# Path parameters are parts of the URL that change.
# They identify a SPECIFIC resource (like a specific user).
# FastAPI automatically converts the string from the URL into the declared type.

@app.get(
    "/users/{user_id}",
    # tags group routes together in the Swagger UI
    tags=["Path Parameters"],
    summary="Get a user by their ID",
)
def get_user(
    # Path(...) adds validation AND documentation to a path parameter.
    # gt=0 means "greater than 0" — FastAPI enforces this automatically.
    # description appears in the Swagger UI docs.
    user_id: int = Path(..., gt=0, description="The unique ID of the user"),
):
    # In a real app, you would query the database here.
    # We return fake data to demonstrate the concept.
    return {"user_id": user_id, "username": f"user_{user_id}"}


# Multiple path parameters in one route
@app.get(
    "/users/{user_id}/tasks/{task_id}",
    tags=["Path Parameters"],
    summary="Get a specific task belonging to a specific user",
)
def get_user_task(
    user_id: int = Path(..., gt=0, description="The user's ID"),
    task_id: int = Path(..., gt=0, description="The task's ID"),
):
    # Notice both path parameters are separate arguments.
    # FastAPI matches them by NAME, not position.
    return {"user_id": user_id, "task_id": task_id}


# ─────────────────────────────────────────────
# 3. QUERY PARAMETERS
# ─────────────────────────────────────────────
# Query parameters appear after the ? in the URL.
# They are used for filtering, sorting, and pagination — not for identifying resources.
# Example: GET /tasks?status=completed&limit=20&page=2

@app.get(
    "/tasks",
    tags=["Query Parameters"],
    summary="List tasks with optional filtering and pagination",
)
def list_tasks(
    # Required query param — the caller MUST include ?status=...
    # (If you want it optional, give it a default value like below)

    # Optional query param with default value
    # Query(...) adds validation and documentation
    limit: int = Query(default=10, ge=1, le=100, description="How many results to return (1–100)"),
    page: int = Query(default=1, ge=1, description="Which page of results to return"),

    # Optional string param — can be None if not provided
    status: Optional[str] = Query(default=None, description="Filter by status: 'active' or 'completed'"),
):
    # ge = greater than or equal to
    # le = less than or equal to
    # These constraints are enforced by FastAPI — no extra validation code needed.
    return {
        "limit": limit,
        "page": page,
        "status": status,
        "results": f"Page {page} of tasks (max {limit} per page)",
    }


# ─────────────────────────────────────────────
# 4. REQUEST BODY
# ─────────────────────────────────────────────
# Request bodies are used with POST, PUT, and PATCH.
# They carry structured data (JSON) that the server needs to create or update a resource.
# We define the expected structure using a Pydantic BaseModel.

# This is the INPUT schema — what the caller must send
class TaskCreate(BaseModel):
    # Field(...) makes a field required with no default
    # min_length and max_length are enforced automatically by Pydantic
    title: str = Field(..., min_length=1, max_length=200, description="The task's title")

    # Optional field — the caller can omit this
    description: Optional[str] = Field(default=None, max_length=1000)

    # Boolean with a sensible default
    completed: bool = Field(default=False)

    # Example tells Swagger UI what a good request looks like
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Write unit tests",
                "description": "Cover all service functions with pytest",
                "completed": False,
            }
        }
    }


@app.post(
    "/tasks",
    tags=["Request Body"],
    summary="Create a new task",
    # status_code=201 means "Created" — more accurate than the default 200 "OK"
    status_code=201,
)
def create_task(
    # FastAPI knows this is a body parameter because it is a Pydantic model type.
    # It will automatically parse, validate, and inject it.
    task: TaskCreate,
):
    # task.title, task.description, task.completed are all validated at this point.
    # In a real app, you would save to the database here.
    return {
        "id": 99,          # Fake ID — in real app, DB generates this
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
    }


# ─────────────────────────────────────────────
# 5. COMBINING ALL THREE
# ─────────────────────────────────────────────
# A real-world endpoint often combines path + query + body.
# FastAPI figures out which is which based on type:
#   - Pydantic model → body
#   - Simple type matching a path variable name → path param
#   - Simple type NOT in path → query param

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None)
    completed: Optional[bool] = Field(default=None)


@app.patch(
    "/users/{user_id}/tasks/{task_id}",
    tags=["Combined"],
    summary="Partially update a task (combining path, query, and body)",
)
def update_task(
    user_id: int = Path(..., gt=0),   # from URL path
    task_id: int = Path(..., gt=0),   # from URL path
    notify: bool = Query(default=False, description="Send notification after update?"),  # query param
    task: TaskUpdate = Body(...),      # from JSON body
):
    return {
        "user_id": user_id,
        "task_id": task_id,
        "notify": notify,
        "updates": task.model_dump(exclude_none=True),  # only include fields that were actually sent
    }
