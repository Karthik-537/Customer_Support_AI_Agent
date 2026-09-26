"""Gemini client wrapper for LLM interactions."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around Gemini with the response contract used by the agent."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Ollama client.

        Args:
            api_key: Gemini API key. Defaults to GEMINI_API_KEY.
            model: Gemini model name. Defaults to GEMINI_MODEL or gemini-2.5-flash.
        """
        resolved_api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_api_key:
            raise ValueError("GEMINI_API_KEY must be set to use Gemini")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=resolved_api_key)
        logger.info("Initialized Gemini client with model=%s", self.model)

    def generate_response(
        self, contents: List | str,
        user_id: str,
        memory_content: Optional[Dict[str, list]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        prompt: Optional[str] = None,
        response_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a response from the LLM.

        Args:
            contents: List of contents.
            user_id: customer's id
            memory_content: Contains both short and long term memories
            tools: Optional list of tool definitions for function calling.
            prompt: system prompt
            response_type: Fixing our response type

        Returns:
            Response dictionary containing the LLM's response and any tool calls.
        """
        try:
            logger.info("Sending request to Gemini with %s messages", len(contents))
            if tools:
                logger.info("Providing %s tools to Gemini", len(tools))
            from app.agent.prompts import get_system_prompt

            system_instruction = get_system_prompt(
                short_term_memories=memory_content["short_term_memories"],
                long_term_memories=memory_content["long_term_memories"],
                user_id=user_id
            ) if not prompt else prompt
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or None,
                tools=[types.Tool(function_declarations=[self._convert_tool(tool) for tool in tools])]
                if tools else None,
            )
            if response_type:
                config.response_mime_type = response_type
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            logger.info("Received response from Gemini")
            return self._convert_response(response)

        except Exception as e:
            logger.error("Error calling Gemini: %s", e)
            raise

    @staticmethod
    def _convert_tool(tool: Dict[str, Any]) -> types.FunctionDeclaration:
        function = tool["function"]
        return types.FunctionDeclaration(
            name=function["name"],
            description=function.get("description"),
            parameters_json_schema=function.get("parameters"),
        )

    @staticmethod
    def _convert_response(response: Any) -> Dict[str, Any]:
        parts = response.candidates[0].content.parts if response.candidates else []
        tool_calls = []
        for index, part in enumerate(parts):
            function_call = getattr(part, "function_call", None)
            if function_call:
                tool_calls.append({
                    "id": function_call.id,
                    "function": {
                        "name": function_call.name,
                        "arguments": dict(function_call.args or {}),
                    },
                })
        return {
            "content": response.candidates[0].content if response.candidates else None,
            "tool_calls": tool_calls,
            "text": response.text if response.text else ""
        }


def get_gemini_client() -> GeminiClient:
    """Get a Gemini client configured from environment variables.

    Returns:
        GeminiClient instance configured from environment variables.
    """
    return GeminiClient()
