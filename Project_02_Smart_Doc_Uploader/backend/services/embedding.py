"""
Project 02 — Service: Embedding
================================
Wraps the sentence-transformers model for encoding text into vectors.
"""

from sentence_transformers import SentenceTransformer
from config import get_settings
import logging
import time

logger = logging.getLogger(__name__)

settings = get_settings()

# Load model once at import time (cached for all requests)
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-loads the embedding model on first use."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}...")
        start = time.perf_counter()
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        elapsed = time.perf_counter() - start
        logger.info(f"Model loaded in {elapsed:.1f}s (dim={_model.get_sentence_embedding_dimension()})")
    return _model


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Encodes a list of texts into embedding vectors.
    Returns list of float lists (JSON-serializable, pgvector-compatible).
    """
    if not texts:
        return []

    model = get_model()
    start = time.perf_counter()

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # unit-length vectors for cosine similarity
    )

    elapsed = time.perf_counter() - start
    logger.info(f"Embedded {len(texts)} texts in {elapsed:.2f}s ({len(texts)/elapsed:.0f} texts/sec)")

    return [emb.tolist() for emb in embeddings]


def embed_query(query: str) -> list[float]:
    """Encodes a single search query into an embedding vector."""
    model = get_model()
    embedding = model.encode(query, normalize_embeddings=True)
    return embedding.tolist()
