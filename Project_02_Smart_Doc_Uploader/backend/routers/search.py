"""
Project 02 — Router: Search
==============================
Semantic search endpoint.
"""

from fastapi import APIRouter
from database import DB
import schemas
from services.search import semantic_search

router = APIRouter()


@router.post("/", response_model=schemas.SearchResponse,
             summary="Semantic search across all indexed documents")
async def search(request: schemas.SearchRequest, db: DB):
    """
    Searches across all indexed documents using semantic similarity.

    The query is embedded using the same model used during ingestion,
    and matched against all stored chunk embeddings using cosine distance.

    Returns ranked results with similarity scores and source citations.
    """
    return await semantic_search(db=db, request=request)
