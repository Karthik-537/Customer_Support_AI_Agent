"""Vector retrieval against a local Qdrant collection.

This module queries embeddings for RAG to retrieve relevant document chunks.
"""

import logging
from typing import Any, Dict, List

from app.rag.embeddings import embed_text
from app.rag.qdrant_store import COLLECTION_NAME, search_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def search_knowledge_base(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    collection_name: str = COLLECTION_NAME,
    embedding_model: str = "all-MiniLM-L6-v2"
) -> List[Dict[str, Any]]:
    """Search the knowledge base for relevant chunks.

    Args:
        query: The search query text.
        top_k: Maximum number of results to return.
        score_threshold: Minimum similarity score (0-1).
        collection_name: Name of the Qdrant collection.
        embedding_model: Name of the embedding model to use.

    Returns:
        List of relevant chunks with metadata:
        [
            {
                "text": str,
                "source": str,
                "page": int,
                "chunk_index": int,
                "score": float
            }
        ]
    """
    logger.info(f"Searching knowledge base for: {query[:100]}...")

    # Generate embedding for the query
    query_embedding = embed_text(query, embedding_model)

    # Search Qdrant
    results = search_chunks(
        query_embedding=query_embedding,
        collection_name=collection_name,
        limit=top_k,
        score_threshold=score_threshold
    )

    logger.info(f"Found {len(results)} relevant chunks")
    return results
