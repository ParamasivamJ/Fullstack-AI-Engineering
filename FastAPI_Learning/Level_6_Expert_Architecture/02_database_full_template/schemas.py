"""
Level 6 — Schemas (Pydantic for PostgreSQL Models)
====================================================

These schemas bridge the SQLAlchemy models and the API layer.

Key pattern:
  DB Model (SQLAlchemy) ← → Schema (Pydantic)
  models.py            ← → schemas.py

NEVER use SQLAlchemy models directly in your API layer.
Always convert through a Pydantic schema to control what is exposed.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


# ─────────────────────────────────────────────
# ENUMS (match the database constraint values)
# ─────────────────────────────────────────────

class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


class UserTier(str, Enum):
    free = "free"
    pro = "pro"


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


# ─────────────────────────────────────────────
# USER SCHEMAS
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    """Input: what the client sends to create a user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr  # EmailStr validates email format automatically
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Input: what the client sends to update a user. All fields optional."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)


class UserOut(BaseModel):
    """Output: what the API returns for a user. Password is excluded."""
    id: UUID
    username: str
    email: str
    role: UserRole
    tier: UserTier
    is_active: bool
    created_at: datetime

    # from_attributes=True allows creating this from a SQLAlchemy model object
    # (SQLAlchemy objects have attributes, not dict keys)
    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Minimal public profile — used in comment authors, task owners etc."""
    id: UUID
    username: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# TASK SCHEMAS
# ─────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: int = Field(default=1, ge=1, le=5)


class TaskUpdate(BaseModel):
    """All fields optional — partial updates only."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)


class TaskOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    completed: bool
    priority: int
    owner_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    """Paginated task list — always wrap lists in a pagination envelope."""
    total: int
    page: int
    per_page: int
    items: list[TaskOut]


# ─────────────────────────────────────────────
# DOCUMENT SCHEMAS (for RAG)
# ─────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    """A document chunk — returned in RAG search results."""
    id: UUID
    content: str
    page_number: Optional[int]
    chunk_index: int
    # We never return the raw embedding vector to the client
    # (it is huge — 384 floats — and the client doesn't need it)

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# RAG QUERY SCHEMAS
# ─────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RAGSourceChunk(BaseModel):
    """A retrieved chunk WITH its similarity score — returned in RAG responses."""
    chunk_id: UUID
    document_name: str
    content: str
    similarity_score: float
    page_number: Optional[int]


class RAGQueryResponse(BaseModel):
    answer: str
    answer_type: str  # "grounded" | "no_context" | "fallback"
    sources: list[RAGSourceChunk]
    retrieval_count: int


# ─────────────────────────────────────────────
# CONVERSATION SCHEMAS
# ─────────────────────────────────────────────

class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    session_id: str
    messages: list[MessageOut]
    total_tokens: int
