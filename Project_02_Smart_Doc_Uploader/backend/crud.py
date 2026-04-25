"""
Project 02 — CRUD Layer
========================
All database queries live here. Routes never touch SQLAlchemy directly.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from uuid import UUID
from typing import Optional

import models


# ─── Document CRUD ───────────────────────────────────────────────

async def create_document(
    db: AsyncSession,
    filename: str,
    content_type: str,
    file_size_bytes: int,
    storage_path: str,
    owner_id: str = "default_user",
) -> models.Document:
    """Creates a new document record with status='uploaded'."""
    doc = models.Document(
        filename=filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        storage_path=storage_path,
        owner_id=owner_id,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, doc_id: UUID) -> Optional[models.Document]:
    result = await db.execute(
        select(models.Document).where(models.Document.id == doc_id)
    )
    return result.scalar_one_or_none()


async def get_documents(
    db: AsyncSession,
    owner_id: str = "default_user",
) -> tuple[list[models.Document], int]:
    """Returns all documents for a user."""
    query = select(models.Document).where(
        models.Document.owner_id == owner_id
    ).order_by(models.Document.created_at.desc())

    result = await db.execute(query)
    docs = list(result.scalars().all())

    return docs, len(docs)


async def update_document_status(
    db: AsyncSession,
    doc_id: UUID,
    status: str,
    chunk_count: int = 0,
    page_count: int = 0,
    error_message: str = None,
):
    """Updates the processing status of a document."""
    doc = await get_document(db, doc_id)
    if doc:
        doc.status = status
        doc.chunk_count = chunk_count
        doc.page_count = page_count
        doc.error_message = error_message
        await db.commit()


async def delete_document(db: AsyncSession, doc_id: UUID) -> bool:
    """Deletes a document and all its chunks (cascade)."""
    doc = await get_document(db, doc_id)
    if not doc:
        return False
    await db.delete(doc)
    await db.commit()
    return True


# ─── Chunk CRUD ──────────────────────────────────────────────────

async def create_chunks_batch(
    db: AsyncSession,
    document_id: UUID,
    chunks: list[dict],
) -> int:
    """
    Batch insert chunks with embeddings.
    Each chunk dict should have: content, page_number, chunk_index, embedding
    """
    chunk_objects = [
        models.DocumentChunk(
            document_id=document_id,
            content=c["content"],
            page_number=c.get("page_number"),
            chunk_index=c["chunk_index"],
            embedding=c["embedding"],
        )
        for c in chunks
    ]
    db.add_all(chunk_objects)
    await db.commit()
    return len(chunk_objects)


async def delete_chunks_by_document(db: AsyncSession, document_id: UUID):
    """Deletes all chunks for a document (for reprocessing)."""
    await db.execute(
        delete(models.DocumentChunk).where(
            models.DocumentChunk.document_id == document_id
        )
    )
    await db.commit()


async def search_chunks(
    db: AsyncSession,
    query_embedding: list[float],
    owner_id: str = "default_user",
    top_k: int = 5,
    score_threshold: float = 0.3,
    document_ids: Optional[list[str]] = None,
    content_types: Optional[list[str]] = None,
) -> list[tuple[models.DocumentChunk, float, str]]:
    """
    Semantic search: finds the most similar chunks to a query embedding.
    Returns list of (chunk, similarity_score, document_filename) tuples.
    """
    cosine_distance = models.DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - cosine_distance).label("similarity")

    query = (
        select(models.DocumentChunk, similarity, models.Document.filename)
        .join(models.Document, models.DocumentChunk.document_id == models.Document.id)
        .where(
            models.Document.owner_id == owner_id,
            models.Document.status == "indexed",
            (1 - cosine_distance) > score_threshold,
        )
        .order_by(cosine_distance)
        .limit(top_k)
    )

    # Optional: filter by specific documents
    if document_ids:
        uuid_ids = [UUID(did) for did in document_ids]
        query = query.where(models.Document.id.in_(uuid_ids))

    # Optional: filter by content type
    if content_types:
        query = query.where(models.Document.content_type.in_(content_types))

    result = await db.execute(query)
    return [
        (row.DocumentChunk, float(row.similarity), row.filename)
        for row in result
    ]
