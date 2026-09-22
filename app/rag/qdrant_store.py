"""Qdrant vector storage for RAG pipeline.

This module handles interaction with Qdrant for storing and retrieving document chunks.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Collection name for company knowledge
COLLECTION_NAME = "company_knowledge"

# Qdrant client instance
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    """Get or create the Qdrant client instance.

    Args:
        host: Qdrant server host.
        port: Qdrant server port.

    Returns:
        QdrantClient instance.
    """
    global _qdrant_client

    if _qdrant_client is None:
        logger.info(f"Connecting to Qdrant at {host}:{port}")
        _qdrant_client = QdrantClient(host=host, port=port)
        logger.info("Connected to Qdrant successfully")

    return _qdrant_client


def create_collection(
    collection_name: str = COLLECTION_NAME,
    vector_size: int = 384,
    recreate: bool = False
) -> None:
    """Create a Qdrant collection for storing document chunks.

    Args:
        collection_name: Name of the collection to create.
        vector_size: Dimension of the embedding vectors.
        recreate: If True, delete and recreate the collection.
    """
    client = get_qdrant_client()

    # Check if collection exists
    collections = client.get_collections().collections
    collection_exists = any(col.name == collection_name for col in collections)

    if collection_exists:
        if recreate:
            logger.info(f"Deleting existing collection: {collection_name}")
            client.delete_collection(collection_name)
        else:
            logger.info(f"Collection {collection_name} already exists")
            return

    logger.info(f"Creating collection: {collection_name} with vector_size={vector_size}")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )
    logger.info(f"Collection {collection_name} created successfully")


def generate_chunk_id(chunk: Dict[str, Any]) -> str:
    """Generate a stable unique ID for a chunk.

    Uses a hash of the chunk content and metadata to ensure
    the same chunk always gets the same ID.

    Args:
        chunk: Chunk dictionary with text, source, page, chunk_index.

    Returns:
        Stable unique ID as a string.
    """
    # Create a string representation of the chunk
    chunk_str = f"{chunk.get('text', '')}{chunk.get('source', '')}{chunk.get('page', '')}{chunk.get('chunk_index', '')}"

    # Generate hash
    hash_object = hashlib.md5(chunk_str.encode())
    hash_hex = hash_object.hexdigest()

    return hash_hex


def upload_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    collection_name: str = COLLECTION_NAME
) -> int:
    """Upload document chunks to Qdrant.

    Args:
        chunks: List of chunk dictionaries with metadata.
        embeddings: List of embedding vectors (same length as chunks).
        collection_name: Name of the Qdrant collection.

    Returns:
        Number of chunks uploaded.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks must match number of embeddings")

    client = get_qdrant_client()

    # Prepare points for upload
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = generate_chunk_id(chunk)

        point = PointStruct(
            id=chunk_id,
            vector=embedding,
            payload={
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "page": chunk.get("page", 1),
                "chunk_index": chunk.get("chunk_index", 0)
            }
        )
        points.append(point)

    # Upload in batches
    batch_size = 100
    uploaded_count = 0

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        uploaded_count += len(batch)
        logger.info(f"Uploaded batch {i//batch_size + 1}: {len(batch)} points")

    logger.info(f"Total chunks uploaded: {uploaded_count}")
    return uploaded_count


def search_chunks(
    query_embedding: List[float],
    collection_name: str = COLLECTION_NAME,
    limit: int = 5,
    score_threshold: float = 0.0
) -> List[Dict[str, Any]]:
    """Search for similar chunks in Qdrant.

    Args:
        query_embedding: Embedding vector for the query.
        collection_name: Name of the Qdrant collection.
        limit: Maximum number of results to return.
        score_threshold: Minimum similarity score (0-1).

    Returns:
        List of search results with metadata:
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
    client = get_qdrant_client()

    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=limit,
        score_threshold=score_threshold
    )

    results = []
    for result in search_results:
        payload = result.payload
        results.append({
            "text": payload.get("text", ""),
            "source": payload.get("source", ""),
            "page": payload.get("page", 1),
            "chunk_index": payload.get("chunk_index", 0),
            "score": result.score
        })

    logger.info(f"Found {len(results)} chunks with score >= {score_threshold}")
    return results


def get_collection_info(collection_name: str = COLLECTION_NAME) -> Dict[str, Any]:
    """Get information about a collection.

    Args:
        collection_name: Name of the Qdrant collection.

    Returns:
        Dictionary with collection information.
    """
    client = get_qdrant_client()

    try:
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "config": info.config
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        return {"error": str(e)}


def delete_collection(collection_name: str = COLLECTION_NAME) -> None:
    """Delete a Qdrant collection.

    Args:
        collection_name: Name of the collection to delete.
    """
    client = get_qdrant_client()

    try:
        client.delete_collection(collection_name)
        logger.info(f"Collection {collection_name} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise
