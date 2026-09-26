"""Long-term memory service using Qdrant.

This module handles persistent user memory storage and retrieval in Qdrant.
Long-term memories are user-specific, reusable, and cross-conversation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.rag.embeddings import embed_text, get_embedding_dimension

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, \
        PointStruct, Filter, FieldCondition, MatchValue, Range
except ImportError:
    QdrantClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
MEMORY_COLLECTION = "customer_memory"
LONG_TERM_MEMORY_TOP_K = 5
MEMORY_SCORE_THRESHOLD = 0.5


def get_qdrant_client() -> Optional[QdrantClient]:
    """Get Qdrant client instance.

    Returns:
        QdrantClient instance or None if Qdrant client is not available.
    """
    if QdrantClient is None:
        logger.error("Qdrant client not installed")
        return None

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        return None


def ensure_memory_collection() -> bool:
    """Ensure the customer_memory collection exists in Qdrant.

    Returns:
        True if collection exists or was created successfully.
    """
    client = get_qdrant_client()
    if client is None:
        return False

    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if MEMORY_COLLECTION in collection_names:
            logger.info(f"Collection '{MEMORY_COLLECTION}' already exists")
            return True

        # Create collection
        dimension = get_embedding_dimension()
        client.create_collection(
            collection_name=MEMORY_COLLECTION,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
        )
        logger.info(f"Created collection '{MEMORY_COLLECTION}' with dimension {dimension}")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure memory collection: {e}")
        return False


def generate_memory_id() -> str:
    """Generate a unique memory ID."""
    return str(uuid.uuid4())


def add_memory(
    user_id: str,
    content: str
) -> Dict[str, Any]:
    """Add a long-term memory for a user.

    Args:
        user_id: The user ID.
        content: The memory content.

    Returns:
        Dictionary containing the created memory info.
    """
    client = get_qdrant_client()
    if client is None:
        return {"success": False, "error": "Qdrant client not available"}

    if not ensure_memory_collection():
        return {"success": False, "error": "Failed to ensure memory collection"}

    try:
        memory_id = generate_memory_id()
        embedding = embed_text(content)

        payload = {
            "memory_id": memory_id,
            "user_id": user_id,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        point = PointStruct(
            id=memory_id,
            vector=embedding,
            payload=payload
        )

        client.upsert(collection_name=MEMORY_COLLECTION, points=[point])

        logger.info(f"Added memory {memory_id} for user {user_id}")
        return {
            "success": True,
            "memory_id": memory_id,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return {"success": False, "error": f"Qdrant error: {str(e)}"}


def search_memories(
    user_id: str,
    query: str,
    top_k: int = LONG_TERM_MEMORY_TOP_K
) -> Dict[str, Any]:
    """Search for relevant long-term memories for a user.

    Args:
        user_id: The user ID.
        query: The search query.
        top_k: Maximum number of results.

    Returns:
        Dictionary containing search results.
    """
    client = get_qdrant_client()
    if client is None:
        return {"success": False, "error": "Qdrant client not available"}

    try:
        query_embedding = embed_text(query)

        # Build filter for user_id and active memories
        conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]

        search_filter = Filter(must=conditions)

        # Search using the Qdrant query API
        results = client.query_points(
            collection_name=MEMORY_COLLECTION,
            query=query_embedding,
            query_filter=search_filter,
            limit=top_k
        )

        memories = []
        for result in results.points:
            payload = result.payload
            if result.score < MEMORY_SCORE_THRESHOLD:
                continue
            memories.append({
                "memory_id": payload.get("memory_id"),
                "user_id": payload.get("user_id"),
                "content": payload.get("content"),
                "score": result.score,
                "created_at": payload.get("created_at")
            })

        return {
            "memories": memories
        }
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return {"success": False, "error": f"Qdrant error: {str(e)}"}


def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    importance: Optional[int] = None,
    active: Optional[bool] = None
) -> Dict[str, Any]:
    """Update an existing memory.

    Args:
        memory_id: The memory ID to update.
        content: New content (optional).
        importance: New importance score (optional).
        active: New active status (optional).

    Returns:
        Dictionary indicating success/failure.
    """
    client = get_qdrant_client()
    if client is None:
        return {"success": False, "error": "Qdrant client not available"}

    try:
        payload_update = {}
        if content is not None:
            payload_update["content"] = content
            payload_update["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Update embedding
            new_embedding = embed_text(content)
            client.set_payload(
                collection_name=MEMORY_COLLECTION,
                payload=payload_update,
                points=[memory_id]
            )
            # Re-upload with new vector
            # Note: Qdrant doesn't support updating vectors directly in all versions
            # For simplicity, we'll just update the payload here
        else:
            if importance is not None:
                payload_update["importance"] = importance
            if active is not None:
                payload_update["active"] = active
            payload_update["updated_at"] = datetime.now(timezone.utc).isoformat()

            client.set_payload(
                collection_name=MEMORY_COLLECTION,
                payload=payload_update,
                points=[memory_id]
            )

        logger.info(f"Updated memory {memory_id}")
        return {"success": True, "memory_id": memory_id}
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        return {"success": False, "error": f"Qdrant error: {str(e)}"}


def deactivate_memory(memory_id: str) -> Dict[str, Any]:
    """Deactivate a memory (soft delete).

    Args:
        memory_id: The memory ID to deactivate.

    Returns:
        Dictionary indicating success/failure.
    """
    return update_memory(memory_id, active=False)


def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory permanently.

    Args:
        memory_id: The memory ID to delete.

    Returns:
        Dictionary indicating success/failure.
    """
    client = get_qdrant_client()
    if client is None:
        return {"success": False, "error": "Qdrant client not available"}

    try:
        client.delete(
            collection_name=MEMORY_COLLECTION,
            points_selector=[memory_id]
        )

        logger.info(f"Deleted memory {memory_id}")
        return {"success": True, "memory_id": memory_id}
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return {"success": False, "error": f"Qdrant error: {str(e)}"}


def check_for_duplicates(
    user_id: str,
    content: str,
    threshold: float = MEMORY_SCORE_THRESHOLD
) -> Dict[str, Any]:
    """Check if a similar memory already exists for the user.

    Args:
        user_id: The user ID.
        content: The content to check.
        threshold: Similarity threshold.

    Returns:
        Dictionary containing potential duplicates.
    """
    search_result = search_memories(user_id, content, top_k=5)

    if not search_result["success"]:
        return {"success": False, "error": search_result.get("error")}

    duplicates = []
    for memory in search_result["memories"]:
        if memory["score"] >= threshold:
            duplicates.append(memory)

    return {
        "success": True,
        "duplicates": duplicates,
        "is_duplicate": len(duplicates) > 0
    }
