"""Core AI agent orchestration.

This module coordinates LLM calls, tool use, and the agent loop.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agent.llm import OllamaClient, get_ollama_client
from app.agent.prompts import get_system_prompt
from app.agent.rag_interface import format_rag_context
from app.agent.tool_registry import execute_tool
from app.agent.tool_schemas import get_tool_schemas
from app.memory.context_builder import build_context
from app.memory.conversation_memory import add_message, get_or_create_conversation
from app.memory.memory_extractor import extract_memory_candidates
from app.memory.memory_processor import process_memory_candidates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomerSupportAgent:
    """Customer support AI agent with tool calling capabilities."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """Initialize the customer support agent.

        Args:
            ollama_client: Optional Ollama client. If not provided, a default one will be created.
        """
        self.llm_client = ollama_client or get_ollama_client()
        self.tool_schemas = get_tool_schemas()
        self.system_prompt = get_system_prompt()
        logger.info("Initialized CustomerSupportAgent")

    def process_message(
        self,
        user_message: str,
        user_id: int,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a user message through the agent with memory support.

        Args:
            user_message: The user's message.
            user_id: The user ID.
            conversation_id: Optional conversation ID. If not provided, a new one is created.
            conversation_history: Optional list of previous conversation messages (deprecated, use conversation_id).

        Returns:
            Dictionary containing the agent's response and metadata.
        """
        logger.info(f"Processing user message: {user_message[:100]}...")

        # Step 1: Get or create conversation
        conv_result = get_or_create_conversation(user_id, conversation_id)
        if not conv_result.get("success"):
            logger.error(f"Failed to get/create conversation: {conv_result.get('error')}")
            return {
                "success": False,
                "error": conv_result.get("error"),
                "response": "I'm sorry, I'm having trouble with conversation tracking. Please try again."
            }

        active_conversation_id = conv_result["conversation_id"]

        # Step 2: Build context with long-term and short-term memory
        context = build_context(
            system_prompt=self.system_prompt,
            user_id=user_id,
            conversation_id=active_conversation_id,
            user_message=user_message,
            include_long_term_memory=True
        )

        messages = context["messages"]

        # Step 3: Agent loop: handle tool calls until final response
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent iteration {iteration}")

            # Get response from LLM
            try:
                response = self.llm_client.generate_response(messages, self.tool_schemas)
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                return {
                    "success": False,
                    "error": f"LLM error: {str(e)}",
                    "response": "I'm sorry, I'm having trouble connecting to my language model. Please try again later."
                }

            # Extract the message content and tool calls
            if not response.get("message"):
                logger.error("Invalid response from LLM: no message field")
                return {
                    "success": False,
                    "error": "Invalid LLM response",
                    "response": "I received an invalid response from my language model. Please try again."
                }

            assistant_message = response["message"]

            # Check if the LLM requested tool calls
            tool_calls = assistant_message.get("tool_calls", [])

            if not tool_calls:
                # No tool calls, this is the final response
                logger.info("No tool calls requested, returning final response")
                content = assistant_message.get("content", "")

                # Step 4: Store conversation messages
                add_message(active_conversation_id, "user", user_message)
                add_message(active_conversation_id, "assistant", content)

                # Step 5: Extract and process long-term memory (non-blocking)
                try:
                    candidates = extract_memory_candidates(user_message)
                    if candidates:
                        process_memory_candidates(
                            user_id=user_id,
                            candidates=candidates,
                            source_conversation_id=active_conversation_id
                        )
                except Exception as e:
                    logger.warning(f"Memory extraction failed (non-blocking): {e}")

                return {
                    "success": True,
                    "response": content,
                    "tool_calls": [],
                    "iterations": iteration,
                    "conversation_id": active_conversation_id,
                    "long_term_memories_used": len(context.get("long_term_memories", []))
                }

            # Add assistant message with tool calls to conversation
            messages.append(assistant_message)

            # Execute tool calls
            logger.info(f"LLM requested {len(tool_calls)} tool call(s)")

            for tool_call in tool_calls:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                if not tool_name:
                    logger.warning("Tool call missing function name")
                    continue

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                try:
                    # Execute the tool
                    tool_result = execute_tool(tool_name, **tool_args)
                    logger.info(f"Tool result: {tool_result}")

                    # Special handling for RAG results
                    if tool_name == "retrieve_company_knowledge" and tool_result.get("success"):
                        # Format RAG results as context for the LLM
                        rag_context = format_rag_context(tool_result.get("results", []))
                        tool_content = f"COMPANY KNOWLEDGE:\n\n{rag_context}"
                    else:
                        tool_content = str(tool_result)

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "content": tool_content,
                        "tool_call_id": tool_call.get("id", "")
                    })

                except ValueError as e:
                    logger.error(f"Tool execution error: {e}")
                    error_message = f"Error executing tool '{tool_name}': {str(e)}"
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.get("id", "")
                    })
                except Exception as e:
                    logger.error(f"Unexpected error executing tool: {e}")
                    error_message = f"Unexpected error executing tool '{tool_name}': {str(e)}"
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.get("id", "")
                    })

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return {
            "success": False,
            "error": "Max iterations reached",
            "response": "I'm sorry, I'm having trouble processing your request. Please try again."
        }


def get_agent() -> CustomerSupportAgent:
    """Get a configured customer support agent instance.

    Returns:
        CustomerSupportAgent instance configured with default settings.
    """
    return CustomerSupportAgent()
