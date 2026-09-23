"""Context builder for combining short-term and long-term memory.

This module builds the Qwen3 context from system instructions, long-term memories,
recent conversation messages, and the current user message.
"""

import logging
from typing import Any, Dict

from app.memory.conversation_memory import get_recent_messages
from app.memory.long_term_memory import search_memories, LONG_TERM_MEMORY_TOP_K

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CONVERSATION_HISTORY_LIMIT = 10


def build_context(
    system_prompt: str,
    user_id: int,
    conversation_id: str,
    user_message: str,
    include_long_term_memory: bool = True
) -> Dict[str, Any]:
    """Build the complete context for the agent.

    Args:
        system_prompt: The system prompt/instructions.
        user_id: The user ID.
        conversation_id: The conversation ID.
        user_message: The current user message.
        include_long_term_memory: Whether to include long-term memory.

    Returns:
        Dictionary containing the built context.
    """

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    long_term_memories = []
    if include_long_term_memory:
        memory_result = search_memories(user_id, user_message, top_k=LONG_TERM_MEMORY_TOP_K)
        if memory_result.get("success"):
            long_term_memories = memory_result.get("memories", [])

            if long_term_memories:
                memory_context = "\n\nUSER PREFERENCES AND CONTEXT:\n"
                for memory in long_term_memories:
                    memory_context += f"- {memory.get('content')}\n"
                messages.append({"role": "system", "content": memory_context})
                logger.info(f"Included {len(long_term_memories)} long-term memories")

    # Recent conversation messages
    recent_messages = get_recent_messages(conversation_id, limit=CONVERSATION_HISTORY_LIMIT)


    # Add long-term memory context if available
    if long_term_memories:
        memory_context = "USER PREFERENCES AND CONTEXT:\n"
        for memory in long_term_memories:
            memory_context += f"- {memory.get('content')}\n"
        messages.append({"role": "system", "content": memory_context})

    # Add conversation history
    for msg in recent_messages:
        messages.append({
            "role": msg.get("role",""),
            "content": msg.get("content","")
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    return {
        "system_prompt": system_prompt,
        "long_term_memories": long_term_memories,
        "conversation_messages": recent_messages,
        "messages": messages,
        "user_message": user_message
    }


def format_context_summary(context: Dict[str, Any]) -> str:
    """Format a human-readable summary of the context.

    Args:
        context: The context dictionary from build_context.

    Returns:
        A formatted string summary.
    """
    parts = []

    parts.append(f"User message: {context.get('user_message', '')}")
    parts.append(f"Conversation messages: {len(context.get('conversation_messages', []))}")
    parts.append(f"Long-term memories: {len(context.get('long_term_memories', []))}")

    if context.get('long_term_memories'):
        parts.append("\nLong-term memory details:")
        for memory in context['long_term_memories']:
            parts.append(f"  - {memory.get('content')} (score: {memory.get('score', 0):.2f})")

    return "\n".join(parts)
