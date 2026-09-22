"""Text chunking for RAG pipeline.

This module implements text chunking with overlap for better retrieval.
"""

import logging
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    source: str = "",
    page: int = 1
) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks.

    Overlap is useful because it ensures that important information
    that might be split across chunk boundaries is preserved in both
    adjacent chunks. This improves retrieval quality by providing more
    context for semantic search.

    Args:
        text: The text to chunk.
        chunk_size: Target character count per chunk (default: 500).
        overlap: Character overlap between chunks (default: 100).
        source: Source document name for metadata.
        page: Page number for metadata.

    Returns:
        List of chunk dictionaries with metadata:
        [
            {
                "text": str,
                "source": str,
                "page": int,
                "chunk_index": int
            }
        ]
    """
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate end position for this chunk
        end = start + chunk_size

        # If this is the last chunk, take whatever remains
        if end > len(text):
            end = len(text)

        # Extract the chunk
        chunk_text = text[start:end]

        # Only add non-empty chunks
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "source": source,
                "page": page,
                "chunk_index": chunk_index
            })
            chunk_index += 1

        # Move start position with overlap
        # If we're at the end, break to avoid infinite loop
        if end >= len(text):
            break

        start = end - overlap

        # Ensure we make progress (avoid infinite loop with small chunks)
        if start <= chunk_index * (chunk_size - overlap):
            start = end

    logger.info(f"Created {len(chunks)} chunks from {len(text)} characters (chunk_size={chunk_size}, overlap={overlap})")
    return chunks


def chunk_documents(documents: List[Dict[str, Any]], chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
    """Chunk multiple documents.

    Args:
        documents: List of document dictionaries with 'text', 'source', and 'page' keys.
        chunk_size: Target character count per chunk (default: 500).
        overlap: Character overlap between chunks (default: 100).

    Returns:
        List of all chunks from all documents.
    """
    all_chunks = []

    for doc in documents:
        text = doc.get("text", "")
        source = doc.get("source", "")
        page = doc.get("page", 1)

        chunks = chunk_text(text, chunk_size, overlap, source, page)
        all_chunks.extend(chunks)

    logger.info(f"Total chunks created from {len(documents)} documents: {len(all_chunks)}")
    return all_chunks
