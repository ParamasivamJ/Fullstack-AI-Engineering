"""
Level 6 — Production Database: PostgreSQL + pgvector
=====================================================

This is the production-grade database setup you will use in all AI projects.

PostgreSQL: industry-standard relational database
SQLAlchemy 2: modern Python ORM (async-capable)
pgvector: adds vector similarity search INSIDE PostgreSQL
Alembic: database migration tool (schema versioning)

WHY pgvector instead of a separate vector DB?
  - One less service to manage
  - All your data in one place (user, task, embedding)
  - Full SQL joins between regular data and vectors
  - Good enough for < 1 million vectors
  (Use Qdrant when you need > 10M vectors or advanced filtering)

SETUP:
  pip install sqlalchemy asyncpg pgvector psycopg2-binary alembic

  Run PostgreSQL with pgvector:
    docker run -d --name pgvector \
      -e POSTGRES_DB=aiapp \
      -e POSTGRES_USER=aiuser \
      -e POSTGRES_PASSWORD=aipass \
      -p 5432:5432 \
      pgvector/pgvector:pg16
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import NullPool
import os

# ─────────────────────────────────────────────
# DATABASE URL PATTERNS
# ─────────────────────────────────────────────

# Synchronous (simpler, use with regular 'def' route functions)
SYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aiuser:aipass@localhost:5432/aiapp"
)

# Asynchronous (use with 'async def' route functions for max performance)
# Note: replace 'postgresql' with 'postgresql+asyncpg'
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    "postgresql+asyncpg://aiuser:aipass@localhost:5432/aiapp"
)

# ─────────────────────────────────────────────
# SYNC ENGINE (for development / scripts)
# ─────────────────────────────────────────────

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    # Connection pool settings — how many DB connections to keep open
    pool_size=10,        # keep 10 connections ready at all times
    max_overflow=20,     # allow up to 20 extra connections under heavy load
    pool_timeout=30,     # wait up to 30s for a connection before erroring
    pool_recycle=1800,   # recycle connections after 30 min (prevents stale connections)
    echo=False,          # set to True to log all SQL queries (useful for debugging)
)

SyncSessionLocal = sessionmaker(
    autocommit=False,  # we manage commits manually — safer for transactions
    autoflush=False,   # don't flush (write) automatically — we control when
    bind=sync_engine,
)

# ─────────────────────────────────────────────
# ASYNC ENGINE (for production FastAPI)
# ─────────────────────────────────────────────

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_recycle=1800,
    echo=False,
    # NullPool is used in serverless environments (Lambda, Cloud Run)
    # where connections can't be shared between requests
    # poolclass=NullPool,  # uncomment for serverless
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
)

# ─────────────────────────────────────────────
# BASE CLASS FOR ALL MODELS
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this.
    It provides the metadata registry that tracks all table definitions.
    """
    pass


# ─────────────────────────────────────────────
# DEPENDENCY: sync DB session
# ─────────────────────────────────────────────

def get_db() -> Session:  # type: ignore
    """
    Yields a synchronous DB session for the duration of one request.
    Use this in regular (non-async) route functions.
    """
    db = SyncSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # undo any partial changes if something went wrong
        raise
    finally:
        db.close()  # always close, whether success or failure


# ─────────────────────────────────────────────
# DEPENDENCY: async DB session
# ─────────────────────────────────────────────

async def get_async_db() -> AsyncSession:  # type: ignore
    """
    Yields an async DB session. Use this in async route functions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────
# PGVECTOR SETUP
# ─────────────────────────────────────────────

async def setup_pgvector():
    """
    Enables the pgvector extension in PostgreSQL.
    Run this ONCE when the app starts (in startup event).
    """
    async with async_engine.connect() as conn:
        # CREATE EXTENSION IF NOT EXISTS is idempotent — safe to run repeatedly
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()


# ─────────────────────────────────────────────
# CREATE ALL TABLES
# ─────────────────────────────────────────────

async def create_tables():
    """
    Creates all tables defined in models.py.
    In production, use Alembic migrations instead (see alembic/ directory).
    create_all is fine for development and learning.
    """
    async with async_engine.begin() as conn:
        # import here to avoid circular imports
        from models import Base as ModelsBase  # type: ignore
        await conn.run_sync(ModelsBase.metadata.create_all)


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

async def check_db_health() -> bool:
    """Returns True if the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
