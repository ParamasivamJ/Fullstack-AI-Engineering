"""
Project 02 — Smart Document Uploader: Main Application
========================================================
uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

from config import get_settings
from database import init_db
from routers import documents, search

# ─── Logging Setup ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ─── Lifespan (Startup / Shutdown) ───────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup: initializes DB, enables pgvector, creates tables."""
    logger.info(f"🚀 Starting {settings.APP_NAME} ({settings.APP_ENV})")
    await init_db()
    logger.info("✅ Database initialized (pgvector enabled, tables created)")

    # Pre-load the embedding model so the first request isn't slow
    from services.embedding import get_model
    get_model()
    logger.info("✅ Embedding model loaded")

    yield  # App is running

    logger.info("👋 Shutting down")


# ─── App Factory ─────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Upload PDF/DOCX/TXT documents and search them semantically using embeddings and pgvector.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
)

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include Routers ─────────────────────────────────────────────

app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(search.router, prefix="/search", tags=["Search"])


# ─── Root + Health ───────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /documents/upload",
            "list": "GET /documents",
            "status": "GET /documents/{id}/status",
            "search": "POST /search",
        },
    }


@app.get("/health", tags=["System"])
async def health():
    from database import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIMENSION,
    }
