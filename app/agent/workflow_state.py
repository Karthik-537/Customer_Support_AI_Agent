"""Structured internal workflow state for multi-step agent execution.

This module tracks operations, tool results, RAG contexts, and prevents
duplicate write actions during a single agent workflow run.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Operations that modify state (write actions) requiring idempotency protection
WRITE_OPERATIONS = {
    "cancel_order",
    "create_support_ticket",
    "escalate_to_human",
}


@dataclass
class WorkflowState:
    """Internal state representing an active multi-step agent workflow."""

    user_id: int
    conversation_id: str
    original_user_message: str
    iteration_count: int = 0
    executed_actions: List[Dict[str, Any]] = field(default_factory=list)
    executed_write_actions: Set[Tuple[str, Tuple[Tuple[str, str], ...]]] = field(default_factory=set)
    rag_results: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False
    error: Optional[str] = None

    def _generate_action_signature(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        """Generate a deterministic signature for a tool action to detect duplicates.

        Args:
            tool_name: Name of the tool.
            tool_args: Tool arguments dictionary.

        Returns:
            Hashable tuple signature for the action.
        """
        # Normalize args into sorted tuple of (key, string_value)
        normalized_args = tuple(sorted((k, str(v)) for k, v in tool_args.items()))
        return (tool_name, normalized_args)

    def is_duplicate_write_action(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """Check whether this tool call is a duplicate write action.

        Args:
            tool_name: Name of the tool to check.
            tool_args: Arguments passed to the tool.

        Returns:
            True if this is a write operation that was already executed in this workflow.
        """
        if tool_name not in WRITE_OPERATIONS:
            return False

        signature = self._generate_action_signature(tool_name, tool_args)
        return signature in self.executed_write_actions

    def record_action(self, tool_name: str, tool_args: Dict[str, Any], tool_result: Dict[str, Any]) -> None:
        """Record the execution and result of a tool action.

        Args:
            tool_name: Name of the executed tool.
            tool_args: Arguments passed to the tool.
            tool_result: Result dictionary returned by the tool.
        """
        action_record = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "success": tool_result.get("success", False),
            "result_summary": str(tool_result)[:200],
        }
        self.executed_actions.append(action_record)
        self.tool_results.append(tool_result)

        if tool_name == "retrieve_company_knowledge":
            self.rag_results.append(tool_result)

        if tool_name in WRITE_OPERATIONS:
            signature = self._generate_action_signature(tool_name, tool_args)
            self.executed_write_actions.add(signature)
            logger.info(f"Recorded write action in workflow: {signature}")

