"""Ollama client wrapper for LLM interactions."""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from ollama import Client

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper around Ollama client for LLM interactions."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Ollama client.

        Args:
            host: Ollama server host URL. Defaults to OLLAMA_HOST env var or localhost:11434.
            model: Model name to use. Defaults to OLLAMA_MODEL env var or qwen3:8b.
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.client = Client(host=self.host)
        logger.info(f"Initialized Ollama client with host={self.host}, model={self.model}")

    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a response from the LLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            tools: Optional list of tool definitions for function calling.

        Returns:
            Response dictionary containing the LLM's response and any tool calls.
        """
        try:
            logger.info(f"Sending request to Ollama with {len(messages)} messages")
            if tools:
                logger.info(f"Providing {len(tools)} tools to LLM")

            response = self.client.chat(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
            )

            logger.info("Received response from Ollama")
            return response

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            raise


def get_ollama_client() -> OllamaClient:
    """Get a configured Ollama client instance.

    Returns:
        OllamaClient instance configured from environment variables.
    """
    return OllamaClient()
