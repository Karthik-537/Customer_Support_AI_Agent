"""RAG interface for the AI agent.

This module provides a clean interface for the agent to retrieve
company knowledge through the existing RAG system.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from app.rag.retriever import search_knowledge_base

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retrieve_company_knowledge(query: str) -> Dict[str, Any]:
    """Retrieve company knowledge for a given query.

    This function provides a clean interface for the agent to access
    the existing RAG system. It retrieves relevant company policy
    information from the knowledge base.

    Args:
        query: The knowledge-related query to search for.

    Returns:
        Dictionary containing retrieval results:
        {
            "success": bool,
            "query": str,
            "results": [
                {
                    "text": str,
                    "source": str,
                    "page": int,
                    "score": float
                }
            ],
            "retrieved_count": int,
            "error": str (if failed)
        }
    """
    # Get RAG configuration from environment
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    score_threshold = float(os.getenv("RAG_SCORE_THRESHOLD", "0.50"))

    logger.info(f"Retrieving company knowledge for: {query[:100]}...")

    try:
        # Call the existing RAG retriever
        results = search_knowledge_base(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold
        )

        logger.info(f"Retrieved {len(results)} relevant chunks")

        return {
            "success": True,
            "query": query,
            "results": results,
            "retrieved_count": len(results)
        }

    except Exception as e:
        logger.error(f"Error retrieving company knowledge: {e}")
        return {
            "success": False,
            "query": query,
            "results": [],
            "retrieved_count": 0,
            "error": f"Knowledge retrieval error: {str(e)}"
        }


def format_rag_context(results: List[Dict[str, Any]]) -> str:
    """Format RAG results for inclusion in LLM context.

    Args:
        results: List of retrieved chunks with metadata.

    Returns:
        Formatted context string for the LLM.
    """
    if not results:
        return "No relevant company information found in the knowledge base."

    context_parts = []
    for i, result in enumerate(results, 1):
        source = result.get("source", "unknown")
        page = result.get("page", 1)
        text = result.get("text", "")

        context_part = f"[Source: {source}, Page: {page}]\n{text}"
        context_parts.append(context_part)

    return "\n\n---\n\n".join(context_parts)
