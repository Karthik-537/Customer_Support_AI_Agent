"""Memory processing for filtering, deduplication, and conflict resolution.

This module processes memory candidates before storage in long-term memory.
"""

import logging
from typing import Any, Dict, List, Optional

from app.memory.long_term_memory import (
    add_memory,
    check_for_duplicates,
    deactivate_memory,
    MEMORY_DUPLICATE_SIMILARITY_THRESHOLD
)
from app.memory.memory_extractor import filter_by_importance, LONG_TERM_MEMORY_MIN_IMPORTANCE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_memory_candidate(
    user_id: int,
    candidate: Dict[str, Any],
    source_conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process a single memory candidate.

    This function:
    1. Checks for duplicates
    2. Handles conflicts (deactivates old conflicting memories)
    3. Stores the new memory

    Args:
        user_id: The user ID.
        candidate: The memory candidate dictionary.
        source_conversation_id: Optional source conversation ID.

    Returns:
        Dictionary indicating the result of processing.
    """
    memory_type = candidate.get("type", "fact")
    content = candidate.get("content", "")
    importance = candidate.get("importance", 5)

    # Check for duplicates
    duplicate_check = check_for_duplicates(user_id, content)

    if duplicate_check.get("is_duplicate"):
        duplicates = duplicate_check.get("duplicates", [])

        # Check for conflicts (same type, different content)
        conflicting = [
            d for d in duplicates
            if d.get("memory_type") == memory_type
            and d.get("content") != content
        ]

        if conflicting:
            # Deactivate conflicting memories
            for conflict in conflicting:
                conflict_id = conflict.get("memory_id")
                if conflict_id:
                    deactivate_memory(conflict_id)
                    logger.info(f"Deactivated conflicting memory {conflict_id}")

            # Store new memory
            result = add_memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                importance=importance,
                source_conversation_id=source_conversation_id
            )

            return {
                "status": "updated",
                "deactivated_count": len(conflicting),
                "new_memory": result
            }
        else:
            # Exact duplicate, skip
            logger.info(f"Skipping duplicate memory for user {user_id}")
            return {
                "status": "skipped",
                "reason": "duplicate"
            }

    # No duplicates, store new memory
    result = add_memory(
        user_id=user_id,
        memory_type=memory_type,
        content=content,
        importance=importance,
        source_conversation_id=source_conversation_id
    )

    return {
        "status": "created",
        "new_memory": result
    }


def process_memory_candidates(
    user_id: int,
    candidates: List[Dict[str, Any]],
    source_conversation_id: Optional[str] = None,
    min_importance: int = LONG_TERM_MEMORY_MIN_IMPORTANCE
) -> Dict[str, Any]:
    """Process multiple memory candidates.

    Args:
        user_id: The user ID.
        candidates: List of memory candidates.
        source_conversation_id: Optional source conversation ID.
        min_importance: Minimum importance score threshold.

    Returns:
        Dictionary containing processing results.
    """
    # Filter by importance
    filtered = filter_by_importance(candidates, min_importance)

    if not filtered:
        return {
            "success": True,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "candidates": []
        }

    results = []
    created_count = 0
    updated_count = 0
    skipped_count = 0

    from app.rag.qdrant_store import create_collection, get_collection_info
    from long_term_memory import MEMORY_COLLECTION

    collection_info = get_collection_info(MEMORY_COLLECTION)
    if not collection_info:
        from app.rag.ingest import EMBEDDING_MODEL
        from app.rag.embeddings import get_embedding_dimension

        embedding_dim = get_embedding_dimension(EMBEDDING_MODEL)
        create_collection(
            collection_name=MEMORY_COLLECTION,
            vector_size=embedding_dim,
            recreate=False
        )
    for candidate in filtered:
        result = process_memory_candidate(user_id, candidate, source_conversation_id)
        results.append(result)

        status = result.get("status")
        if status == "created":
            created_count += 1
        elif status == "updated":
            updated_count += 1
        elif status == "skipped":
            skipped_count += 1

    logger.info(
        f"Processed {len(filtered)} candidates: "
        f"{created_count} created, {updated_count} updated, {skipped_count} skipped"
    )

    return {
        "success": True,
        "processed": len(filtered),
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "results": results
    }
