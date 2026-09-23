"""Memory system for customer support AI agent.

This package provides:
- ConversationMemory: SQLite-based short-term conversation history
- LongTermMemory: Qdrant-based long-term user memory
- MemoryExtractor: LLM-based memory extraction
- MemoryProcessor: Memory filtering, deduplication, and conflict resolution
- ContextBuilder: Combines short-term and long-term memory for agent context
"""

from app.memory.conversation_memory import (
    add_message,
    clear_conversation,
    create_conversation,
    delete_conversation,
    generate_conversation_id,
    get_conversation,
    get_messages,
    get_or_create_conversation,
    get_recent_messages,
    list_user_conversations,
    update_conversation,
)

__all__ = [
    "add_message",
    "clear_conversation",
    "create_conversation",
    "delete_conversation",
    "generate_conversation_id",
    "get_conversation",
    "get_messages",
    "get_or_create_conversation",
    "get_recent_messages",
    "list_user_conversations",
    "update_conversation",
]
