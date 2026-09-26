"""Context builder for combining short-term and long-term memory.

This module builds the Qwen3 context from system instructions, long-term memories,
recent conversation messages, and the current user message.
"""

import logging
from typing import Dict

from app.memory.conversation_memory import get_messages
from app.memory.long_term_memory import search_memories, LONG_TERM_MEMORY_TOP_K

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CONVERSATION_HISTORY_LIMIT = 10


def build_context(
    user_id: str,
    conversation_id: str,
    user_message: str,
) -> Dict[str, list]:
    """Build the complete context for the agent.

    Args:
        user_id: The user ID.
        conversation_id: The conversation ID.
        user_message: The current user message.

    Returns:
        Dictionary containing the built context.
    """
    memory_result = search_memories(user_id, user_message, top_k=LONG_TERM_MEMORY_TOP_K)
    long_term_memories = memory_result.get("memories", [])

    # Recent conversation messages
    conversation_memories = get_messages(conversation_id, limit=CONVERSATION_HISTORY_LIMIT)
    memories = conversation_memories["messages"]
    short_term_memories = []
    for mem in memories:
        short_term_memories.append({
            "user": mem["user_message"],
            "ai_response": mem["response"]
        })
    memory_content = {
        "short_term_memories": short_term_memories,
        "long_term_memories": long_term_memories
    }
    return memory_content
