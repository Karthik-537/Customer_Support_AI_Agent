"""Memory extraction using Gemini.

This module uses the LLM to identify useful long-term memory candidates
from conversation messages.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.agent.llm import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_memory_extraction_prompt(user_message: str, response: str) -> str:
    """Build the system prompt for memory extraction.

    Args:
        user_message: The user's message to analyze.

    Returns:
        The extraction prompt.
    """
    return f"""
You are a long-term memory extractor for a customer-support AI agent.

Analyze the user message and assistant response and decide whether the interaction contains information worth remembering for future conversations.

USER MESSAGE:
{user_message}

ASSISTANT RESPONSE:
{response}

Store a memory ONLY when the information is:
- User-specific
- Useful in future conversations
- Likely to remain relevant over time
- Explicitly stated or clearly supported by the user

Do NOT store:
- Temporary issues or one-time requests
- Order IDs, ticket IDs, or other temporary details
- Greetings or normal conversation
- General product/company information
- Information inferred only by the assistant
- Information that is unlikely to help in a future conversation

If suitable, create a short, clear, self-contained memory.
If multiple independent facts are worth remembering, create separate memories.

Return ONLY valid JSON:

{
    "memories": [
        {
            "content": "..."
        }
    ]
}

If nothing is suitable for long-term memory:

{
    "memories": []
}
"""


def add_long_term_memories(
        user_message: str, response: str, user_id: int) -> List[Dict[str, Any]]:
    """Extract long-term memory candidates from a user message.

    Args:
        user_message: The user's message to analyze.
        response: The llm response
        user_id: user's id

    Returns:
        List of memory candidate dictionaries, or empty list if extraction fails.
    """
    try:
        prompt = _build_memory_extraction_prompt(user_message=user_message, response=response)

        client = GeminiClient()
        response = client.generate_response(
            contents=[], prompt=prompt, response_type="application/json"
        )
        text = response["text"]
        memory_data = json.loads(text) if text else {}
        memories = memory_data.get("memories")
        from app.memory.long_term_memory import add_memory
        if memories:
            for mem in memories:
                content = mem.get("content")
                add_memory(
                    user_id=user_id,
                    content=content
                )
    except Exception as e:
        logger.error(f"Error during memory extraction: {e}")
        return []

