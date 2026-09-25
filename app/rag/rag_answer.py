"""RAG answer generation using LLM.

This module generates answers to user queries using retrieved context.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agent.llm import GeminiClient, get_gemini_client
from app.agent.prompts import get_rag_prompt
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def construct_context(chunks: List[Dict[str, Any]]) -> str:
    """Construct a context string from retrieved chunks.

    Args:
        chunks: List of retrieved chunks with metadata.

    Returns:
        Formatted context string for the LLM.
    """
    if not chunks:
        return "No relevant information found in the knowledge base."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        page = chunk.get("page", 1)
        text = chunk.get("text", "")
        score = chunk.get("score", 0.0)

        context_part = f"[Source: {source}, Page: {page}, Score: {score:.2f}]\n{text}"
        context_parts.append(context_part)

    return "\n\n---\n\n".join(context_parts)


def generate_rag_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    gemini_client: Optional[GeminiClient] = None
) -> Dict[str, Any]:
    """Generate an answer to a query using retrieved chunks.

    Args:
        query: The user's question.
        chunks: Retrieved chunks from the knowledge base.
        gemini_client: Optional Gemini client. If not provided, a default one will be created.

    Returns:
        Dictionary containing the generated answer and metadata.
    """
    logger.info(f"Generating RAG answer for query: {query[:100]}...")

    # Get or create Gemini client
    if gemini_client is None:
        gemini_client = get_gemini_client()

    # Construct context from chunks
    context = construct_context(chunks)

    # Build messages for LLM
    system_prompt = get_rag_prompt()
    user_message = f"""Company Knowledge:

{context}

Question: {query}

Please answer the question based on the provided knowledge."""

    contents = [
        types.Content(
            role="user", parts=[types.Part(text=user_message)]
        )
    ]

    try:
        # Generate response from LLM
        response = gemini_client.generate_response(contents=contents, prompt=system_prompt)

        # Extract the answer
        if response.get("message") and response["message"].get("content"):
            answer = response["message"]["content"]
            logger.info("RAG answer generated successfully")
            return {
                "success": True,
                "answer": answer,
                "chunks_used": len(chunks),
                "context_length": len(context)
            }
        else:
            logger.error("Invalid response from LLM")
            return {
                "success": False,
                "error": "Invalid LLM response",
                "answer": "I'm sorry, I couldn't generate an answer from the provided information."
            }

    except Exception as e:
        logger.error(f"Error generating RAG answer: {e}")
        return {
            "success": False,
            "error": f"LLM error: {str(e)}",
            "answer": "I'm sorry, I'm having trouble processing your request. Please try again later."
        }


def rag_pipeline(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    embedding_model: str = "all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """Complete RAG pipeline: retrieve chunks and generate answer.

    Args:
        query: The user's question.
        top_k: Number of chunks to retrieve.
        score_threshold: Minimum similarity score.
        embedding_model: Name of the embedding model.

    Returns:
        Dictionary containing the answer and retrieval metadata.
    """
    from app.rag.retriever import search_knowledge_base

    logger.info(f"Starting RAG pipeline for query: {query[:100]}...")

    # Step 1: Retrieve relevant chunks
    chunks = search_knowledge_base(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        embedding_model=embedding_model
    )

    # Step 2: Generate answer using retrieved chunks
    result = generate_rag_answer(query, chunks)

    # Add retrieval metadata to result
    result["retrieved_chunks"] = len(chunks)
    result["chunks"] = chunks

    return result
