"""
Project 02 — Pydantic Schemas
==============================
Request/Response schemas for the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


# ─── Document Schemas ────────────────────────────────────────────

class DocumentOut(BaseModel):
    """Response schema for a document (no file data, no embeddings)."""
    id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    chunk_count: int
    page_count: int
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    """Paginated list of documents."""
    total: int
    items: list[DocumentOut]


class DocumentStatus(BaseModel):
    """Lightweight status check response."""
    id: UUID
    status: str
    chunk_count: int
    error_message: Optional[str] = None


# ─── Search Schemas ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Input for semantic search."""
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # Optional metadata filters
    document_ids: Optional[list[str]] = None
    content_types: Optional[list[str]] = None


class SearchResultItem(BaseModel):
    """A single search result — a chunk with its score and citation."""
    chunk_id: UUID
    content: str
    document_id: UUID
    document_name: str
    page_number: Optional[int]
    chunk_index: int
    similarity_score: float


class SearchResponse(BaseModel):
    """Full search response with results and metadata."""
    query: str
    results: list[SearchResultItem]
    total_found: int
    search_time_ms: float
    sources_summary: str  # "Based on: doc1.pdf (p.3), doc2.txt (p.1)"
