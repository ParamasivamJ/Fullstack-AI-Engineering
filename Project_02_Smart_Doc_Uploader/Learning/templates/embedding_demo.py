"""
Template: Embeddings Demo
===========================
Run standalone to see embeddings in action:
  pip install sentence-transformers numpy
  python embedding_demo.py
"""

import numpy as np
import time


def main():
    """Demonstrates embedding generation and similarity computation."""
    from sentence_transformers import SentenceTransformer

    print("=" * 60)
    print("EMBEDDINGS DEMO")
    print("=" * 60)

    # ── Load Model ────────────────────────────────────────────────
    print("\n📦 Loading model: all-MiniLM-L6-v2...")
    start = time.perf_counter()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"   Loaded in {time.perf_counter() - start:.1f}s")
    print(f"   Embedding dimensions: {model.get_sentence_embedding_dimension()}")
    print(f"   Max sequence length: {model.max_seq_length} tokens")

    # ── Single Embedding ──────────────────────────────────────────
    text = "FastAPI is a modern Python web framework"
    embedding = model.encode(text)
    print(f"\n📐 Embedding shape: {embedding.shape}")
    print(f"   First 5 values: {embedding[:5].round(4)}")
    print(f"   Vector norm (should be ~1.0): {np.linalg.norm(embedding):.4f}")

    # ── Similarity Demo ───────────────────────────────────────────
    print("\n🔍 Similarity Comparison:")
    texts = [
        "FastAPI is a modern Python web framework for APIs",        # similar to query
        "Django is a batteries-included Python web framework",       # related
        "React is a JavaScript library for building user interfaces", # different domain
        "Quantum computing uses qubits for parallel computation",    # unrelated
        "How do I build an API with Python?",                        # semantically similar
    ]

    query = "What is FastAPI?"
    query_embedding = model.encode(query)
    text_embeddings = model.encode(texts)

    print(f"\n   Query: \"{query}\"")
    print(f"   {'─' * 50}")

    similarities = []
    for text, emb in zip(texts, text_embeddings):
        # Cosine similarity (for normalized vectors, this equals dot product)
        similarity = np.dot(query_embedding, emb) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(emb)
        )
        similarities.append((similarity, text))

    # Sort by similarity (descending)
    similarities.sort(reverse=True)

    for score, text in similarities:
        # Visual bar
        bar_len = int(score * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"   {score:.4f} |{bar}| {text[:60]}")

    # ── Batch Performance ─────────────────────────────────────────
    print(f"\n⚡ Batch Encoding Performance:")
    batch_sizes = [10, 100, 500]
    for n in batch_sizes:
        test_texts = [f"This is test sentence number {i}" for i in range(n)]
        start = time.perf_counter()
        model.encode(test_texts, batch_size=64, show_progress_bar=False)
        elapsed = time.perf_counter() - start
        print(f"   {n:>4} texts → {elapsed:.3f}s ({n/elapsed:.0f} texts/sec)")


if __name__ == "__main__":
    main()
