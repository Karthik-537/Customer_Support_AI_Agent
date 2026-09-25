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

# Configuration
LONG_TERM_MEMORY_MIN_IMPORTANCE = 7


def _build_memory_extraction_prompt(user_message: str) -> str:
    """Build the system prompt for memory extraction.

    Args:
        user_message: The user's message to analyze.

    Returns:
        The extraction prompt.
    """
    return f"""You are a memory extraction system for a customer support AI.

Your task is to analyze the user's message and identify information that should be
persisted as long-term memory across future conversations.

Long-term memories should be:
- User-specific
- Useful and reusable
- Reasonably stable (not one-time information)
- Important for future interactions

GOOD CANDIDATES for long-term memory:
- User preferences (e.g., "I prefer email communication")
- User facts (e.g., "I work in the healthcare industry")
- Consistent behavior patterns (e.g., "User always asks for technical details")
- Contact information (e.g., "My phone number is 555-1234")

BAD CANDIDATES for long-term memory:
- One-time questions (e.g., "What is the status of order 123?")
- Temporary information (e.g., "I need help right now")
- Generic greetings (e.g., "Hi", "Hello")
- Information already handled by the current conversation

User message:
{user_message}

Return a JSON array of memory candidates. Each candidate should have:
- type: The memory type (e.g., "preference", "fact", "contact")
- content: The memory content as a clear statement
- importance: A score from 1-10 (where 10 is most important)

If no information should be stored as long-term memory, return an empty array: []

Example output:
[
    {{
        "type": "preference",
        "content": "User prefers email communication over phone calls",
        "importance": 8
    }}
]

Return ONLY the JSON array, nothing else."""


def extract_memory_candidates(user_message: str) -> List[Dict[str, Any]]:
    """Extract long-term memory candidates from a user message.

    Args:
        user_message: The user's message to analyze.

    Returns:
        List of memory candidate dictionaries, or empty list if extraction fails.
    """
    try:
        prompt = _build_memory_extraction_prompt(user_message)

        messages = [
            {"role": "system", "content": prompt}
        ]

        client = GeminiClient()
        response = client.generate_response(messages, tools=None)

        content = response.get("message", {}).get("content", "")
        if not content:
            logger.warning("Memory extraction returned no content")
            return []

        # Parse JSON response
        try:
            # Try to extract JSON from the response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            candidates = json.loads(content)

            if not isinstance(candidates, list):
                logger.warning(f"Memory extraction returned non-list: {type(candidates)}")
                return []

            logger.info(f"Extracted {len(candidates)} memory candidates")
            return candidates

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse memory extraction JSON: {e}")
            logger.warning(f"Response content: {content}")
            return []

    except Exception as e:
        logger.error(f"Error during memory extraction: {e}")
        return []


def filter_by_importance(
    candidates: List[Dict[str, Any]],
    min_importance: int = LONG_TERM_MEMORY_MIN_IMPORTANCE
) -> List[Dict[str, Any]]:
    """Filter memory candidates by importance score.

    Args:
        candidates: List of memory candidates.
        min_importance: Minimum importance score.

    Returns:
        Filtered list of memory candidates.
    """
    return [c for c in candidates if c.get("importance", 0) >= min_importance]
