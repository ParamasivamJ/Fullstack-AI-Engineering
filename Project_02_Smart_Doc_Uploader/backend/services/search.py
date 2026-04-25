"""
Project 02 — Service: Search
==============================
Orchestrates the search pipeline: query → embed → vector search → format results.
"""

import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

import crud
import schemas
from services.embedding import embed_query

logger = logging.getLogger(__name__)


async def semantic_search(
    db: AsyncSession,
    request: schemas.SearchRequest,
    owner_id: str = "default_user",
) -> schemas.SearchResponse:
    """
    Full search pipeline:
    1. Embed the query
    2. Search pgvector with filters
    3. Format results with citations
    """
    start = time.perf_counter()

    # Step 1: Embed the query
    query_embedding = embed_query(request.query)

    # Step 2: Vector search with metadata filters
    raw_results = await crud.search_chunks(
        db=db,
        query_embedding=query_embedding,
        owner_id=owner_id,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
        document_ids=request.document_ids,
        content_types=request.content_types,
    )

    # Step 3: Format results
    results = []
    sources = set()

    for chunk, score, doc_filename in raw_results:
        results.append(schemas.SearchResultItem(
            chunk_id=chunk.id,
            content=chunk.content,
            document_id=chunk.document_id,
            document_name=doc_filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            similarity_score=round(score, 4),
        ))
        page_info = f"p.{chunk.page_number}" if chunk.page_number else ""
        sources.add(f"{doc_filename} ({page_info})" if page_info else doc_filename)

    elapsed_ms = (time.perf_counter() - start) * 1000

    sources_summary = "Based on: " + ", ".join(sorted(sources)) if sources else "No relevant documents found"

    logger.info(
        f"Search completed: query='{request.query[:50]}' "
        f"results={len(results)} time={elapsed_ms:.1f}ms"
    )

    return schemas.SearchResponse(
        query=request.query,
        results=results,
        total_found=len(results),
        search_time_ms=round(elapsed_ms, 2),
        sources_summary=sources_summary,
    )
