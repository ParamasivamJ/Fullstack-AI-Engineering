"""
Template: Chunking Strategies Demo
====================================
Run standalone to test chunking on any text:
  python chunking_demo.py
"""

import re


# ─── STRATEGY 1: Fixed-Size ─────────────────────────────────────

def fixed_chunks(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Simple character-based splitting. Fast but low quality."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


# ─── STRATEGY 2: Sentence-Aware ⭐ ──────────────────────────────

def sentence_chunks(text: str, max_size: int = 512, overlap_sentences: int = 2) -> list[str]:
    """
    Groups whole sentences into chunks. Never breaks mid-sentence.
    This is the recommended strategy for most RAG applications.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_size and current:
            chunks.append(" ".join(current))
            current = current[-overlap_sentences:]  # keep last N for overlap
            current_len = sum(len(s) for s in current)

        current.append(sentence)
        current_len += len(sentence)

    if current:
        chunks.append(" ".join(current))

    return chunks


# ─── STRATEGY 3: Recursive Splitting ────────────────────────────

def recursive_chunks(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """
    LangChain-style recursive splitting.
    Tries paragraph boundaries first, then sentences, then words.
    """
    separators = ["\n\n", "\n", ". ", " "]

    def _split(t: str, seps: list[str]) -> list[str]:
        if not seps or len(t) <= size:
            return [t] if t.strip() else []

        sep = seps[0]
        parts = t.split(sep)
        result = []
        current = ""

        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) <= size:
                current = candidate
            else:
                if current:
                    result.append(current.strip())
                if len(part) > size:
                    result.extend(_split(part, seps[1:]))
                    current = ""
                else:
                    current = part

        if current:
            result.append(current.strip())

        return [c for c in result if c]

    return _split(text, separators)


# ─── COMPARISON ──────────────────────────────────────────────────

SAMPLE_TEXT = """
FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints. The key features are automatic documentation, fast execution, and editor support.

FastAPI uses Pydantic for data validation. Pydantic enforces type hints at runtime and provides user-friendly errors when data is invalid. This means every request body is automatically validated before your route function runs.

Dependency injection is a design pattern where a function declares what it needs, and the framework provides it. In FastAPI, you use Depends() to inject database sessions, authentication tokens, and other shared resources into your route functions.

Error handling in production requires consistency. Every error response should follow the same schema. Use custom exception handlers to catch domain-specific exceptions and convert them to standardized JSON responses with error codes that the frontend can switch on.

Background tasks allow you to run code after returning a response. Use BackgroundTasks for simple fire-and-forget jobs like sending emails. Use Celery with Redis for retryable, persistent task queues that survive server restarts.
""".strip()


if __name__ == "__main__":
    print("=" * 60)
    print("CHUNKING STRATEGIES COMPARISON")
    print("=" * 60)
    print(f"\nInput text: {len(SAMPLE_TEXT)} characters\n")

    strategies = [
        ("Fixed-Size (500 chars, 50 overlap)", fixed_chunks(SAMPLE_TEXT, 500, 50)),
        ("Sentence-Aware (512 chars, 2 overlap)", sentence_chunks(SAMPLE_TEXT, 512, 2)),
        ("Recursive (500 chars)", recursive_chunks(SAMPLE_TEXT, 500)),
    ]

    for name, chunks in strategies:
        print(f"\n{'─' * 60}")
        print(f"Strategy: {name}")
        print(f"Chunks produced: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"\n  Chunk {i+1} ({len(chunk)} chars):")
            # Show first 100 chars
            preview = chunk[:100].replace("\n", " ")
            print(f"    \"{preview}...\"")
