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
from app.agent.workflow_state import WorkflowState
from app.memory.context_builder import build_context
from app.memory.conversation_memory import add_message, get_or_create_conversation
from app.memory.memory_extractor import extract_memory_candidates
from app.memory.memory_processor import process_memory_candidates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomerSupportAgent:
    """Customer support AI agent with multi-step tool calling capabilities."""

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
        user_id: Optional[int] = 1,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Process a user message through the agent with multi-step workflow support.

        Args:
            user_message: The user's message.
            user_id: The customer user ID. Defaults to 1.
            conversation_id: Optional conversation ID. If not provided, a new one is created.
            conversation_history: Optional list of previous conversation messages.

        Returns:
            Dictionary containing the agent's response and execution metadata.
        """
        # Handle backward compatibility if conversation_history passed as 2nd positional argument
        if isinstance(user_id, list):
            conversation_history = user_id
            user_id = 1
        elif user_id is None:
            user_id = 1

        logger.info(f"Processing user message for user {user_id}: {user_message[:100]}...")

        # Step 1: Get or create conversation session
        conv_result = get_or_create_conversation(user_id, conversation_id)
        if not conv_result.get("success"):
            logger.error(f"Failed to get/create conversation: {conv_result.get('error')}")
            return {
                "success": False,
                "error": conv_result.get("error"),
                "response": "I'm sorry, I'm having trouble with conversation tracking. Please try again.",
            }

        active_conversation_id = conv_result["conversation_id"]

        # Step 2: Initialize structured internal workflow state
        workflow_state = WorkflowState(
            user_id=user_id,
            conversation_id=active_conversation_id,
            original_user_message=user_message,
        )

        # Step 3: Build context with long-term and short-term memory
        context = build_context(
            system_prompt=self.system_prompt,
            user_id=user_id,
            conversation_id=active_conversation_id,
            user_message=user_message,
            include_long_term_memory=True,
        )

        if conversation_history:
            # Explicit conversation history provided (e.g. from testing or direct call)
            messages = [{"role": "system", "content": self.system_prompt}]
            for msg in conversation_history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
            messages.append({"role": "user", "content": user_message})
        else:
            messages = context["messages"]

        # Step 4: Multi-step agent loop
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            workflow_state.iteration_count = iteration
            logger.info(f"Multi-step agent iteration {iteration}/{max_iterations}")

            # Get response from LLM
            try:
                response = self.llm_client.generate_response(messages, self.tool_schemas)
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                return {
                    "success": False,
                    "error": f"LLM error: {str(e)}",
                    "response": "I'm sorry, I'm having trouble connecting to my language model. Please try again later.",
                }

            # Validate response structure
            if not response.get("message"):
                logger.error("Invalid response from LLM: no message field")
                return {
                    "success": False,
                    "error": "Invalid LLM response",
                    "response": "I received an invalid response from my language model. Please try again.",
                }

            assistant_message = response["message"]
            tool_calls = assistant_message.get("tool_calls", [])

            # If no tool calls requested, LLM has formulated the final customer response
            if not tool_calls:
                logger.info("No tool calls requested, returning final response")
                content = assistant_message.get("content", "")
                workflow_state.completed = True

                # Step 5: Store conversation messages in short-term memory
                add_message(active_conversation_id, "user", user_message)
                add_message(active_conversation_id, "assistant", content)

                # Step 6: Extract and process long-term memory (non-blocking)
                try:
                    candidates = extract_memory_candidates(user_message)
                    if candidates:
                        process_memory_candidates(
                            user_id=user_id,
                            candidates=candidates,
                            source_conversation_id=active_conversation_id,
                        )
                except Exception as e:
                    logger.warning(f"Memory extraction failed (non-blocking): {e}")

                return {
                    "success": True,
                    "response": content,
                    "tool_calls": workflow_state.executed_actions,
                    "iterations": iteration,
                    "conversation_id": active_conversation_id,
                    "long_term_memories_used": len(context.get("long_term_memories", [])),
                }

            # Add assistant message with tool calls to conversation context
            messages.append(assistant_message)

            # Step 7: Execute tool calls with idempotency protection
            logger.info(f"LLM requested {len(tool_calls)} tool call(s) at iteration {iteration}")

            for tool_call in tool_calls:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                if not tool_name:
                    logger.warning("Tool call missing function name")
                    continue

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                try:
                    # Check for duplicate write actions within this workflow
                    if workflow_state.is_duplicate_write_action(tool_name, tool_args):
                        logger.warning(
                            f"Prevented duplicate write action '{tool_name}' with args {tool_args}"
                        )
                        tool_result = {
                            "success": False,
                            "error": (
                                f"Action '{tool_name}' has already been performed in this request. "
                                "Do not repeat the same action; proceed with the results already obtained."
                            ),
                            "already_executed": True,
                        }
                    else:
                        tool_result = execute_tool(tool_name, **tool_args)

                    workflow_state.record_action(tool_name, tool_args, tool_result)
                    logger.info(f"Tool {tool_name} execution completed: {tool_result}")

                    # Format RAG results vs operational business tool results
                    if tool_name == "retrieve_company_knowledge" and tool_result.get("success"):
                        rag_context = format_rag_context(tool_result.get("results", []))
                        tool_content = f"COMPANY KNOWLEDGE:\n\n{rag_context}"
                    else:
                        tool_content = str(tool_result)

                    messages.append({
                        "role": "tool",
                        "content": tool_content,
                        "tool_call_id": tool_call.get("id", ""),
                    })

                except ValueError as e:
                    logger.error(f"Tool execution error: {e}")
                    error_message = f"Error executing tool '{tool_name}': {str(e)}"
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.get("id", ""),
                    })
                except Exception as e:
                    logger.error(f"Unexpected error executing tool: {e}")
                    error_message = f"Unexpected error executing tool '{tool_name}': {str(e)}"
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.get("id", ""),
                    })

        # Max iterations reached without a final customer response
        logger.warning(f"Max iterations ({max_iterations}) reached")
        safe_response = (
            "I'm sorry, but I was unable to complete all required steps for your request. "
            "Please contact our customer support team or rephrase your request."
        )

        try:
            add_message(active_conversation_id, "user", user_message)
            add_message(active_conversation_id, "assistant", safe_response)
        except Exception as e:
            logger.warning(f"Failed to record message on max iterations: {e}")

        return {
            "success": False,
            "error": "Max iterations reached",
            "response": safe_response,
            "tool_calls": workflow_state.executed_actions,
            "iterations": iteration,
            "conversation_id": active_conversation_id,
            "long_term_memories_used": len(context.get("long_term_memories", [])),
        }


def get_agent() -> CustomerSupportAgent:
    """Get a configured customer support agent instance.

    Returns:
        CustomerSupportAgent instance configured with default settings.
    """
    return CustomerSupportAgent()
