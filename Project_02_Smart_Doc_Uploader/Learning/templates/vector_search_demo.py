"""
Template: Vector Search Demo (pgvector with SQLAlchemy)
=========================================================
This demo simulates the full search flow without requiring PostgreSQL.
It uses in-memory numpy for vector operations.

For the real pgvector implementation, see the backend/ directory.

Run:
  pip install sentence-transformers numpy
  python vector_search_demo.py
"""

import numpy as np
import time
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a stored document chunk with its embedding."""
    id: str
    content: str
    document_name: str
    page_number: int
    embedding: np.ndarray


class InMemoryVectorDB:
    """
    Simulates pgvector operations using numpy.
    Replace with real pgvector queries in production.
    """

    def __init__(self):
        self.chunks: list[Chunk] = []

    def insert(self, chunk: Chunk):
        self.chunks.append(chunk)

    def cosine_search(self, query_embedding: np.ndarray, top_k: int = 5,
                      threshold: float = 0.3) -> list[tuple[Chunk, float]]:
        """
        Simulates: SELECT *, 1 - (embedding <=> $1) AS similarity
                   FROM document_chunks
                   ORDER BY embedding <=> $1 LIMIT $2;
        """
        if not self.chunks:
            return []

        # Stack all embeddings into a matrix for vectorized computation
        embeddings = np.stack([c.embedding for c in self.chunks])

        # Cosine similarity: dot(A, B) / (||A|| * ||B||)
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        chunk_norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarities = np.dot(chunk_norms, query_norm)

        # Filter by threshold and get top_k
        results = []
        for idx in np.argsort(similarities)[::-1]:  # descending
            score = float(similarities[idx])
            if score < threshold:
                break
            results.append((self.chunks[idx], score))
            if len(results) >= top_k:
                break

        return results

    def filtered_search(self, query_embedding: np.ndarray, document_name: str = None,
                        top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Simulates pre-filtered search:
        WHERE document_name = $1 ORDER BY embedding <=> $2 LIMIT $3
        """
        # Pre-filter
        filtered = self.chunks
        if document_name:
            filtered = [c for c in filtered if c.document_name == document_name]

        if not filtered:
            return []

        embeddings = np.stack([c.embedding for c in filtered])
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        chunk_norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarities = np.dot(chunk_norms, query_norm)

        results = []
        for idx in np.argsort(similarities)[::-1][:top_k]:
            results.append((filtered[idx], float(similarities[idx])))

        return results


def main():
    from sentence_transformers import SentenceTransformer

    print("=" * 60)
    print("VECTOR SEARCH DEMO")
    print("=" * 60)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    db = InMemoryVectorDB()

    # ── Index Some Documents ──────────────────────────────────────
    documents = {
        "fastapi_guide.pdf": [
            "FastAPI is a modern web framework for building APIs with Python.",
            "FastAPI uses Pydantic for automatic data validation and schema generation.",
            "Dependency injection in FastAPI uses the Depends() function.",
            "FastAPI supports async and await for non-blocking I/O operations.",
        ],
        "database_guide.pdf": [
            "PostgreSQL is a powerful open-source relational database.",
            "pgvector adds vector similarity search to PostgreSQL.",
            "SQLAlchemy is a Python ORM for database operations.",
            "Alembic handles database schema migrations for SQLAlchemy.",
        ],
        "python_basics.txt": [
            "Python is a high-level programming language known for readability.",
            "List comprehensions provide a concise way to create lists in Python.",
            "Decorators in Python are functions that modify other functions.",
        ],
    }

    print("\n📥 Indexing documents...")
    chunk_id = 0
    for doc_name, texts in documents.items():
        embeddings = model.encode(texts)
        for i, (text, emb) in enumerate(zip(texts, embeddings)):
            db.insert(Chunk(
                id=f"chunk_{chunk_id}",
                content=text,
                document_name=doc_name,
                page_number=i + 1,
                embedding=emb,
            ))
            chunk_id += 1
    print(f"   Indexed {chunk_id} chunks from {len(documents)} documents")

    # ── Search Demo ───────────────────────────────────────────────
    queries = [
        "How do I validate request data?",
        "What is dependency injection?",
        "How to migrate database schema?",
        "What programming language is easy to learn?",
    ]

    for query in queries:
        print(f"\n{'─' * 60}")
        print(f"🔍 Query: \"{query}\"")

        query_emb = model.encode(query)
        start = time.perf_counter()
        results = db.cosine_search(query_emb, top_k=3, threshold=0.3)
        elapsed_ms = (time.perf_counter() - start) * 1000

        for chunk, score in results:
            bar_len = int(score * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            print(f"   {score:.3f} |{bar}| [{chunk.document_name} p.{chunk.page_number}]")
            print(f"         {chunk.content[:80]}")
        print(f"   ⏱  {elapsed_ms:.1f}ms")

    # ── Filtered Search Demo ──────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("🔍 FILTERED SEARCH: Only in 'fastapi_guide.pdf'")
    query = "How to handle database operations?"
    query_emb = model.encode(query)
    results = db.filtered_search(query_emb, document_name="fastapi_guide.pdf", top_k=3)

    for chunk, score in results:
        print(f"   {score:.3f} | [{chunk.document_name}] {chunk.content[:70]}")


if __name__ == "__main__":
    main()
