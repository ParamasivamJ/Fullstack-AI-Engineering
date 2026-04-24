"""
Level 6 — CRUD Layer (Separated from Routes)
=============================================

EXPERT RULE: Never put database queries inside route functions.
Put them in a dedicated crud.py layer.

WHY?
  - Routes become thin and readable (they just orchestrate)
  - CRUD functions are easily testable (just pass a mock session)
  - Logic can be reused across multiple routes
  - Clear separation: HTTP logic vs. data access logic

This file demonstrates CRUD for: Users, Tasks, Documents, Chunks (with pgvector search)
"""

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.exc import IntegrityError
from pgvector.sqlalchemy import Vector  # type: ignore
from uuid import UUID
from typing import Optional
import uuid

import models
import schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────
# USER CRUD
# ─────────────────────────────────────────────

async def create_user(db: AsyncSession, user_in: schemas.UserCreate) -> models.User:
    """Creates a new user with a hashed password."""
    # Check for duplicates BEFORE trying to insert (better error message)
    existing = await db.execute(
        select(models.User).where(
            (models.User.username == user_in.username) |
            (models.User.email == user_in.email)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Username or email already exists")

    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=pwd_context.hash(user_in.password),
    )
    db.add(new_user)
    await db.commit()

    # refresh loads the server-generated fields (id, created_at) into the object
    await db.refresh(new_user)
    return new_user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    """Fetches a user by username. Returns None if not found."""
    result = await db.execute(
        select(models.User).where(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[models.User]:
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    return result.scalar_one_or_none()


async def verify_user_password(db: AsyncSession, username: str, password: str) -> Optional[models.User]:
    """Returns the user if credentials are valid, None otherwise."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user


# ─────────────────────────────────────────────
# TASK CRUD
# ─────────────────────────────────────────────

async def create_task(db: AsyncSession, task_in: schemas.TaskCreate, owner_id: UUID) -> models.Task:
    task = models.Task(**task_in.model_dump(), owner_id=owner_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_tasks(
    db: AsyncSession,
    owner_id: UUID,
    completed: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[models.Task], int]:
    """
    Returns a page of tasks for a user, with optional completion filter.
    Returns (list_of_tasks, total_count) — total_count is needed for pagination UI.
    """
    query = select(models.Task).where(models.Task.owner_id == owner_id)

    if completed is not None:
        query = query.where(models.Task.completed == completed)

    # Get total count for pagination
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Apply pagination
    result = await db.execute(
        query.offset((page - 1) * per_page).limit(per_page)
    )
    tasks = result.scalars().all()

    return list(tasks), total


async def update_task(
    db: AsyncSession,
    task_id: UUID,
    owner_id: UUID,
    task_in: schemas.TaskUpdate,
) -> Optional[models.Task]:
    """Updates only the provided fields (partial update)."""
    # model_dump(exclude_none=True) returns only fields that were explicitly set
    updates = task_in.model_dump(exclude_none=True)
    if not updates:
        return None  # nothing to update

    result = await db.execute(
        update(models.Task)
        .where(models.Task.id == task_id, models.Task.owner_id == owner_id)
        .values(**updates)
        .returning(models.Task)  # return the updated row
    )
    await db.commit()
    return result.scalar_one_or_none()


async def delete_task(db: AsyncSession, task_id: UUID, owner_id: UUID) -> bool:
    """Deletes a task. Returns True if deleted, False if not found."""
    result = await db.execute(
        delete(models.Task).where(
            models.Task.id == task_id,
            models.Task.owner_id == owner_id,
        )
    )
    await db.commit()
    # rowcount tells us how many rows were deleted
    return result.rowcount > 0


# ─────────────────────────────────────────────
# DOCUMENT CHUNK CRUD (pgvector RAG)
# ─────────────────────────────────────────────

async def create_document_chunk(
    db: AsyncSession,
    document_id: UUID,
    content: str,
    chunk_index: int,
    embedding: list[float],
    page_number: Optional[int] = None,
) -> models.DocumentChunk:
    """Saves a text chunk with its embedding vector to the database."""
    chunk = models.DocumentChunk(
        document_id=document_id,
        content=content,
        chunk_index=chunk_index,
        page_number=page_number,
        embedding=embedding,  # pgvector stores this as a vector type in PostgreSQL
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    return chunk


async def search_similar_chunks(
    db: AsyncSession,
    query_embedding: list[float],
    owner_id: UUID,           # security: only search within this user's documents
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> list[tuple[models.DocumentChunk, float]]:
    """
    Finds the most semantically similar document chunks to a query.

    Uses pgvector's cosine distance operator: <=>
    Cosine distance ranges from 0 (identical) to 2 (opposite).
    Similarity = 1 - cosine_distance

    The SQL this generates:
      SELECT c.*, 1 - (c.embedding <=> :query_vec) AS similarity
      FROM document_chunks c
      JOIN documents d ON c.document_id = d.id
      WHERE d.owner_id = :owner_id
        AND 1 - (c.embedding <=> :query_vec) > :threshold
      ORDER BY c.embedding <=> :query_vec
      LIMIT :top_k;
    """
    # Cosine distance (lower is more similar)
    cosine_distance = models.DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - cosine_distance).label("similarity")

    result = await db.execute(
        select(models.DocumentChunk, similarity)
        .join(models.Document, models.DocumentChunk.document_id == models.Document.id)
        .where(
            models.Document.owner_id == owner_id,
            # Filter: only return chunks above the similarity threshold
            (1 - cosine_distance) > score_threshold,
        )
        .order_by(cosine_distance)   # ascending cosine distance = descending similarity
        .limit(top_k)
    )

    # Returns list of (DocumentChunk, similarity_score) tuples
    return [(row.DocumentChunk, float(row.similarity)) for row in result]
