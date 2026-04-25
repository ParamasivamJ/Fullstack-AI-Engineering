"""
Project 02 — SQLAlchemy Models
===============================
Documents table + DocumentChunks table (with pgvector embedding column).
"""

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, Index, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from database import Base
from config import get_settings
import uuid

settings = get_settings()


class Document(Base):
    """Stores metadata about uploaded documents."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)           # original filename
    content_type = Column(String(100), nullable=False)       # application/pdf, etc.
    file_size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)       # UUID-based safe path
    status = Column(String(20), default="uploaded", nullable=False)
    # status: "uploaded" → "processing" → "indexed" → "failed"
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)

    # For multi-user support (tenant isolation)
    owner_id = Column(String(100), nullable=False, default="default_user", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to chunks — cascade delete
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.filename} [{self.status}]>"


class DocumentChunk(Base):
    """Stores individual text chunks with their vector embeddings."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)

    # THE VECTOR: 384 dimensions for all-MiniLM-L6-v2
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

    # HNSW index for fast approximate nearest neighbor search
    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_document_id", "document_id"),
    )
