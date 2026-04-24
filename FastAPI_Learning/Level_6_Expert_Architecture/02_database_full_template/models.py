"""
Level 6 — SQLAlchemy Models (PostgreSQL + pgvector)
=====================================================

This file defines the database schema using SQLAlchemy ORM.
Each class becomes a table in PostgreSQL.

Key concepts demonstrated:
  - UUID primary keys (more scalable than integer sequences)
  - Timestamps (created_at, updated_at) on every table
  - Foreign key relationships
  - pgvector column type for storing embeddings
  - Indexes for query performance
"""

from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text,
    ForeignKey, DateTime, func, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector  # pip install pgvector
from database import Base
import uuid


# ─────────────────────────────────────────────
# USERS TABLE
# ─────────────────────────────────────────────

class User(Base):
    """Stores user accounts."""
    __tablename__ = "users"

    # UUID primary key is better than Integer for distributed systems
    # and does not leak how many users you have (security)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)

    # NEVER store plain passwords — only the bcrypt hash
    hashed_password = Column(String(255), nullable=False)

    role = Column(String(20), nullable=False, default="user")

    # Subscription tier — used for model access control (Level 4)
    tier = Column(String(20), nullable=False, default="free")

    # is_active allows soft-disabling users without deleting their data
    is_active = Column(Boolean, default=True, nullable=False)

    # server_default=func.now() means PostgreSQL sets this — not Python.
    # This is more reliable in distributed systems.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships — SQLAlchemy loads related objects on demand
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


# ─────────────────────────────────────────────
# TASKS TABLE
# ─────────────────────────────────────────────

class Task(Base):
    """Project 1 style tasks — demonstrates basic relational design."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=1, nullable=False)

    # Foreign key — links each task to one user
    # ondelete="CASCADE" means tasks are deleted when the user is deleted
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship — access task.owner to get the User object
    owner = relationship("User", back_populates="tasks")

    # Composite index — speeds up "get all tasks for user X" queries
    __table_args__ = (
        Index("ix_tasks_owner_completed", "owner_id", "completed"),
    )


# ─────────────────────────────────────────────
# DOCUMENTS TABLE (for RAG projects)
# ─────────────────────────────────────────────

class Document(Base):
    """Stores uploaded documents before they are chunked and indexed."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)  # e.g., "application/pdf"
    file_size_bytes = Column(Integer, nullable=False)

    # Storage path or cloud URL (e.g., "s3://bucket/docs/uuid.pdf")
    storage_path = Column(String(500), nullable=False)

    # Processing status — updated as background ingestion progresses
    status = Column(String(20), default="uploaded", nullable=False)
    # status values: "uploaded" → "processing" → "indexed" → "failed"

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# DOCUMENT CHUNKS TABLE (pgvector)
# ─────────────────────────────────────────────

class DocumentChunk(Base):
    """
    Stores individual text chunks from documents WITH their vector embeddings.
    This is the core of any RAG system.

    Each document is split into chunks (e.g., 512 tokens each),
    and each chunk gets an embedding vector from a model like all-MiniLM-L6-v2.

    The pgvector 'Vector' type stores the embedding and enables
    nearest-neighbour search using the <=> (cosine distance) operator.
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The actual text content of this chunk
    content = Column(Text, nullable=False)

    # Page number in the original document (for citations)
    page_number = Column(Integer, nullable=True)

    # Position of this chunk within the document (for ordering)
    chunk_index = Column(Integer, nullable=False)

    # THE VECTOR EMBEDDING — 384 dimensions for all-MiniLM-L6-v2
    # Change to 1536 for OpenAI text-embedding-3-small
    # Change to 3072 for OpenAI text-embedding-3-large
    embedding = Column(Vector(384), nullable=True)
    # nullable=True because embedding is added in a background task after upload

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="chunks")

    # Vector index — HNSW is the best algorithm for fast approximate nearest-neighbour search
    # cosine operator class is best for sentence embeddings (they are normalized)
    # This index makes vector search fast even with millions of chunks
    __table_args__ = (
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# ─────────────────────────────────────────────
# CONVERSATION MEMORY TABLE
# ─────────────────────────────────────────────

class ConversationMessage(Base):
    """
    Stores chat history for multi-turn AI conversations.
    Used in Project 7 (memory-enabled assistant).
    """
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)  # for trimming long conversations

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Index to efficiently retrieve a session's history in order
        Index("ix_messages_session_created", "session_id", "created_at"),
    )
