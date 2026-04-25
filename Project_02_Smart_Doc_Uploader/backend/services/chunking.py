"""
Project 02 — Service: Text Chunking
=====================================
Sentence-aware chunking with metadata attachment.
"""

import re
import logging

logger = logging.getLogger(__name__)


def chunk_pages(
    pages: list[dict],
    max_chunk_size: int = 512,
    overlap_sentences: int = 2,
) -> list[dict]:
    """
    Takes extracted pages and produces chunks with metadata.

    Input:  [{"page_number": 1, "text": "..."}, ...]
    Output: [{"content": "...", "page_number": 1, "chunk_index": 0}, ...]
    """
    all_chunks = []
    global_index = 0

    for page in pages:
        page_chunks = _sentence_aware_split(
            page["text"],
            max_chunk_size=max_chunk_size,
            overlap_sentences=overlap_sentences,
        )

        for chunk_text in page_chunks:
            if chunk_text.strip() and len(chunk_text.strip()) > 20:
                all_chunks.append({
                    "content": chunk_text.strip(),
                    "page_number": page["page_number"],
                    "chunk_index": global_index,
                })
                global_index += 1

    logger.info(f"Chunking: {len(pages)} pages → {len(all_chunks)} chunks")
    return all_chunks


def _sentence_aware_split(
    text: str,
    max_chunk_size: int = 512,
    overlap_sentences: int = 2,
) -> list[str]:
    """Splits text at sentence boundaries, never mid-sentence."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text] if text.strip() else []

    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sent_len = len(sentence)

        if current_len + sent_len > max_chunk_size and current:
            chunks.append(" ".join(current))
            # Overlap: keep last N sentences
            current = current[-overlap_sentences:] if overlap_sentences > 0 else []
            current_len = sum(len(s) for s in current)

        current.append(sentence)
        current_len += sent_len

    if current:
        chunks.append(" ".join(current))

    return chunks
