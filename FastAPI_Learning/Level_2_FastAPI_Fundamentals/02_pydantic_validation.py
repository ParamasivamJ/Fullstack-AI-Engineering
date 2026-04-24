"""
Level 2 — Pydantic Validation (Expert Level)
=============================================

Pydantic is the engine FastAPI uses to validate all data.
Understanding it deeply is critical for building AI apps because:
  - LLM inputs and outputs must be validated before and after calling the model
  - Database reads must be filtered before sending to clients
  - Nested documents (for RAG) need complex schema structures

HOW TO RUN:
  uvicorn 02_pydantic_validation:app --reload
  Then open: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from pydantic import (
    BaseModel,
    Field,
    field_validator,   # validate a single field with custom logic
    model_validator,   # validate the whole model (cross-field checks)
    EmailStr,          # built-in email validation (pip install pydantic[email])
    HttpUrl,           # built-in URL validation
)
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

app = FastAPI(title="Level 2: Pydantic Validation")


# ─────────────────────────────────────────────
# 1. ENUMS — constrained string choices
# ─────────────────────────────────────────────
# Instead of validating strings manually, use Enum.
# The API will ONLY accept the exact values defined here.

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


# ─────────────────────────────────────────────
# 2. BASIC MODEL WITH FIELD CONSTRAINTS
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    # Field constraints are validated BEFORE your function runs
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: TaskStatus = Field(default=TaskStatus.todo)

    # Numeric constraints
    priority: int = Field(default=1, ge=1, le=5, description="1=lowest, 5=highest")


# ─────────────────────────────────────────────
# 3. FIELD VALIDATORS — custom validation logic
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    password: str = Field(..., min_length=8)
    role: UserRole = Field(default=UserRole.user)

    # @field_validator runs after type conversion but before the object is created.
    # Use it when built-in constraints are not enough.
    @field_validator("username")
    @classmethod
    def username_must_be_alphanumeric(cls, value: str) -> str:
        # value is already confirmed to be a string by this point
        if not value.replace("_", "").isalnum():
            # Raising ValueError triggers a 422 response automatically
            raise ValueError("Username can only contain letters, numbers, and underscores")
        # Always return the (possibly transformed) value
        return value.lower()  # Store usernames in lowercase — consistent lookup

    @field_validator("password")
    @classmethod
    def password_must_have_digit(cls, value: str) -> str:
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value  # Do NOT return hashed password here — hash in the service layer


# ─────────────────────────────────────────────
# 4. MODEL VALIDATORS — cross-field validation
# ─────────────────────────────────────────────

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

    # model_validator runs after ALL field validators pass.
    # Use it when validation depends on multiple fields at once.
    @model_validator(mode="after")
    def check_dates_are_logical(self) -> "DateRange":
        # 'mode="after"' means self is already the constructed object
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


# ─────────────────────────────────────────────
# 5. NESTED MODELS
# ─────────────────────────────────────────────
# Pydantic models can be nested inside each other.
# FastAPI validates the full nested structure automatically.

class Address(BaseModel):
    street: str
    city: str
    country: str = "India"  # sensible default for your context


class UserProfile(BaseModel):
    username: str
    email: str
    address: Address                 # nested model — expects a JSON object
    tags: List[str] = []             # list of strings — must all be strings
    metadata: dict = {}              # arbitrary key-value pairs — avoid in production; prefer explicit fields


# ─────────────────────────────────────────────
# 6. SEPARATING INPUT AND OUTPUT SCHEMAS
# ─────────────────────────────────────────────
# EXPERT RULE: Never use the same schema for input and output.
# The input schema accepts a password.
# The output schema must NEVER return the password.

class UserIn(BaseModel):
    """Schema for creating a user — includes password."""
    username: str
    password: str
    role: UserRole = UserRole.user


class UserOut(BaseModel):
    """Schema for returning a user — password is EXCLUDED by design."""
    id: int
    username: str
    role: UserRole
    created_at: datetime

    # from_attributes=True allows creating this from a SQLAlchemy model object
    # (The ORM returns objects with attributes, not dicts)
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# 7. LITERAL TYPES — exact value matching
# ─────────────────────────────────────────────
# Use Literal when only specific values are allowed.
# Useful for model selection in AI apps.

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    # Only these exact model strings are accepted — any other value is rejected with 422
    model: Literal["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"] = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8000)


# ─────────────────────────────────────────────
# 8. DEMO ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/tasks", status_code=201, tags=["Tasks"])
def create_task(task: TaskCreate):
    return {"id": 1, **task.model_dump()}


@app.post("/users", status_code=201, tags=["Users"])
def create_user(user: UserCreate):
    # model_dump() converts the Pydantic model to a plain Python dict
    # exclude={"password"} drops the password before logging or returning
    safe_data = user.model_dump(exclude={"password"})
    return {"message": "User created", "user": safe_data}


@app.post("/profiles", status_code=201, tags=["Profiles"])
def create_profile(profile: UserProfile):
    # model_dump(mode="json") converts nested models and special types to JSON-safe dicts
    return profile.model_dump(mode="json")


@app.post("/search-range", tags=["Search"])
def search_by_date(date_range: DateRange):
    return {
        "start": date_range.start_date.isoformat(),
        "end": date_range.end_date.isoformat(),
        "days": (date_range.end_date - date_range.start_date).days,
    }


@app.post("/chat", tags=["AI"])
def chat(req: ChatRequest):
    # At this point: message, model, temperature, max_tokens are all validated
    return {
        "model_selected": req.model,
        "input_tokens_estimate": len(req.message.split()),
        "message": f"Echo: {req.message}",
    }
