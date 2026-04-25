"""
Project 02 — Database Setup (PostgreSQL + pgvector)
=====================================================
Async engine with session factory and dependency injection.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import get_settings
from typing import Annotated
from fastapi import Depends

settings = get_settings()

# Async engine for FastAPI routes
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    echo=settings.DEBUG,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base class for all models
class Base(DeclarativeBase):
    pass


# Dependency: yields an async DB session per request
async def get_db() -> AsyncSession:  # type: ignore
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Type alias for clean route signatures
DB = Annotated[AsyncSession, Depends(get_db)]


# Startup: enable pgvector extension + create tables
async def init_db():
    """Run once at startup: enable pgvector and create all tables."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Import models to register them with Base.metadata
        import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
