"""
Level 4 — RAG Pipeline Template (Production)
=============================================

RAG = Retrieval-Augmented Generation

The pattern:
  1. User sends a question
  2. Convert the question to an embedding (a vector)
  3. Search the vector DB for similar document chunks
  4. Build a prompt: "Given these documents: [chunks]... Answer: [question]"
  5. Send that prompt to the LLM
  6. Return the answer WITH source citations

This is the most important AI engineering pattern.
Everything else in the stack exists to support this pipeline.

HOW TO RUN:
  pip install httpx sentence-transformers qdrant-client
  uvicorn 03_rag_pipeline_template:app --reload

NOTE: This file uses simulated embeddings and a fake vector DB.
      Level 6 will connect to real PostgreSQL + pgvector.
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import hashlib
import json

app = FastAPI(title="Level 4: RAG Pipeline")


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class RAGRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)
    # How many document chunks to retrieve
    top_k: int = Field(default=3, ge=1, le=10)
    # Minimum similarity score — chunks below this are ignored
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    # Whether to include source citations in the response
    include_sources: bool = Field(default=True)


class SourceChunk(BaseModel):
    """A retrieved document chunk with its metadata."""
    chunk_id: str
    document_name: str
    content: str
    similarity_score: float
    page_number: Optional[int] = None


class RAGResponse(BaseModel):
    """The full RAG response — answer + sources."""
    answer: str
    sources: list[SourceChunk]
    # For transparency: show the user which context was used
    context_used: str
    model: str
    retrieval_count: int
    # "grounded" = answer came from retrieved docs
    # "no_context" = no relevant docs found, LLM answered from training
    answer_type: str


# ─────────────────────────────────────────────
# FAKE IMPLEMENTATIONS (replace with real in production)
# ─────────────────────────────────────────────

class FakeEmbeddingModel:
    """
    Simulates a sentence embedding model.
    In production: use sentence-transformers or OpenAI embeddings.

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode(text).tolist()
    """

    def embed(self, text: str) -> list[float]:
        # Return a fake 384-dim vector (real all-MiniLM-L6-v2 is 384-dim)
        # We use the text hash to make it deterministic (same text → same vector)
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val >> i & 0xFF) / 255.0 for i in range(384)]


class FakeVectorDB:
    """
    Simulates a vector database (Qdrant or pgvector).
    Stores document chunks with their embeddings.
    Retrieves the most similar chunks for a given query embedding.

    In production (pgvector):
      SELECT id, content, embedding <=> $1 AS score
      FROM chunks WHERE embedding <=> $1 < 0.5
      ORDER BY score LIMIT $2;

    In production (Qdrant):
      client.search(collection_name="docs", query_vector=embedding, limit=top_k)
    """

    def __init__(self):
        # Fake knowledge base — in production this comes from real document ingestion
        self.chunks = [
            {"id": "chunk_1", "doc": "fastapi_guide.pdf", "content": "FastAPI is a modern Python web framework for building APIs with automatic documentation.", "page": 1},
            {"id": "chunk_2", "doc": "fastapi_guide.pdf", "content": "FastAPI uses Pydantic for data validation and automatic schema generation.", "page": 2},
            {"id": "chunk_3", "doc": "rag_paper.pdf", "content": "Retrieval-Augmented Generation (RAG) combines retrieval with generation to ground answers in facts.", "page": 1},
            {"id": "chunk_4", "doc": "rag_paper.pdf", "content": "RAG reduces hallucinations by providing the LLM with relevant context from a knowledge base.", "page": 3},
            {"id": "chunk_5", "doc": "vector_db.pdf", "content": "pgvector adds vector similarity search to PostgreSQL using the <=> operator.", "page": 1},
        ]

    def search(self, query_embedding: list[float], top_k: int, threshold: float) -> list[SourceChunk]:
        """Returns the top_k most similar chunks above the threshold."""
        # In real implementation: compute cosine similarity against all stored embeddings
        # Here we return fake results with simulated scores
        results = []
        for i, chunk in enumerate(self.chunks[:top_k]):
            score = 0.9 - (i * 0.1)  # fake decreasing similarity scores
            if score >= threshold:
                results.append(SourceChunk(
                    chunk_id=chunk["id"],
                    document_name=chunk["doc"],
                    content=chunk["content"],
                    similarity_score=score,
                    page_number=chunk["page"],
                ))
        return results


class FakeLLM:
    """
    Simulates an LLM.
    In production, replace with:

    import openai
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content
    """

    async def complete(self, system_prompt: str, user_question: str) -> str:
        await asyncio.sleep(1)  # simulate latency
        return (
            f"Based on the provided documents, here is an answer to '{user_question}': "
            f"FastAPI is a modern Python framework that uses Pydantic for validation. "
            f"This answer was grounded in the retrieved context."
        )


# Instantiate our fake services (in production, use dependency injection)
embedding_model = FakeEmbeddingModel()
vector_db = FakeVectorDB()
llm = FakeLLM()


# ─────────────────────────────────────────────
# THE RAG PIPELINE
# ─────────────────────────────────────────────

def build_rag_prompt(question: str, chunks: list[SourceChunk]) -> str:
    """
    Constructs the prompt that instructs the LLM to answer from context only.

    The system prompt is the key to controlling LLM behavior:
    - "Only use the provided context" → reduces hallucinations
    - "If unsure, say I don't know" → prevents confident wrong answers
    - Numbered sources → enables citation in the response
    """
    context_text = "\n\n".join(
        f"[Source {i+1}] {chunk.document_name} (p.{chunk.page_number}):\n{chunk.content}"
        for i, chunk in enumerate(chunks)
    )

    return f"""You are a helpful assistant that answers questions ONLY based on the provided context.

CONTEXT:
{context_text}

INSTRUCTIONS:
- Answer ONLY using information from the context above.
- If the context does not contain enough information to answer, say: "I don't have enough information in my knowledge base to answer this question."
- Cite your sources by referencing [Source N] where applicable.
- Do not make up information not present in the context.

QUESTION: {question}

ANSWER:"""


@app.post("/rag/query", response_model=RAGResponse, tags=["RAG"])
async def rag_query(req: RAGRequest):
    """
    The complete RAG pipeline in one endpoint.

    Flow:
    Question → Embed → Retrieve → Build Prompt → LLM → Return answer + sources
    """

    # ── STEP 1: Embed the question ──────────────────────────────────
    # Convert the question into a vector so we can find similar document chunks
    query_embedding = embedding_model.embed(req.question)

    # ── STEP 2: Retrieve relevant chunks ───────────────────────────
    # Find the top_k most similar document chunks from the vector DB
    retrieved_chunks = vector_db.search(
        query_embedding=query_embedding,
        top_k=req.top_k,
        threshold=req.score_threshold,
    )

    # ── STEP 3: Handle no results ──────────────────────────────────
    if not retrieved_chunks:
        # Option A: Return "I don't know" without calling the LLM (saves cost)
        return RAGResponse(
            answer="I could not find any relevant information in the knowledge base for your question.",
            sources=[],
            context_used="",
            model="none",
            retrieval_count=0,
            answer_type="no_context",
        )

    # ── STEP 4: Build the prompt ───────────────────────────────────
    system_prompt = build_rag_prompt(req.question, retrieved_chunks)

    # ── STEP 5: Call the LLM ───────────────────────────────────────
    # Only NOW do we call the expensive LLM — and only with grounded context
    try:
        answer = await asyncio.wait_for(
            llm.complete(system_prompt, req.question),
            timeout=30.0,  # always set a timeout on LLM calls
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM response timed out")

    # ── STEP 6: Return answer + sources ───────────────────────────
    # Sources are returned so the frontend can display "Based on: fastapi_guide.pdf p.1"
    return RAGResponse(
        answer=answer,
        sources=retrieved_chunks if req.include_sources else [],
        context_used="\n---\n".join(c.content for c in retrieved_chunks),
        model="fake-llm-v1",
        retrieval_count=len(retrieved_chunks),
        answer_type="grounded",
    )


@app.get("/rag/health", tags=["RAG"])
def rag_health():
    """Check that the embedding model and vector DB are reachable."""
    try:
        test_embedding = embedding_model.embed("test")
        return {
            "embedding_model": "ok",
            "embedding_dim": len(test_embedding),
            "vector_db": "ok",
            "chunks_indexed": len(vector_db.chunks),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"RAG service unhealthy: {e}")
