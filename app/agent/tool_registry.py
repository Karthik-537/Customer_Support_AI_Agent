"""Tool registry for mapping tool names to Python functions.

This module provides a secure mapping between tool names and their
corresponding Python functions, preventing arbitrary code execution.
"""

from typing import Any, Callable, Dict, Optional

from app.agent.rag_interface import retrieve_company_knowledge
from app.tools.product_tools import check_product_by_name
from app.tools.order_tools import (
    check_order_cancellation,
    get_my_orders,
    get_orders_by_product_name,
)
from app.tools.ticket_tools import (
    create_support_ticket,
    get_support_tickets_by_product_name,
    get_ticket_status_by_product_name,
)


# Tool registry mapping tool names to their Python functions
TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "check_order_cancellation": check_order_cancellation,
    "get_my_orders": get_my_orders,
    "get_orders_by_product_name": get_orders_by_product_name,
    "check_product_by_name": check_product_by_name,
    "create_support_ticket": create_support_ticket,
    "get_support_tickets_by_product_name": get_support_tickets_by_product_name,
    "get_ticket_status_by_product_name": get_ticket_status_by_product_name,
    "retrieve_company_knowledge": retrieve_company_knowledge,
}


def get_tool_function(tool_name: str) -> Optional[Callable[..., Dict[str, Any]]]:
    """Get a tool function by name.

    Args:
        tool_name: The name of the tool to retrieve.

    Returns:
        The tool function if found, None otherwise.
    """
    return TOOL_REGISTRY.get(tool_name)


def execute_tool(tool_name: str, **kwargs: Any) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments.

    Args:
        tool_name: The name of the tool to execute.
        **kwargs: Arguments to pass to the tool function.

    Returns:
        The result dictionary from the tool function.

    Raises:
        ValueError: If the tool name is not found in the registry.
    """
    tool_func = get_tool_function(tool_name)
    if tool_func is None:
        raise ValueError(f"Tool '{tool_name}' not found in registry")

    return tool_func(**kwargs)


def get_available_tools() -> list[str]:
    """Get a list of all available tool names.

    Returns:
        List of tool names that can be executed.
    """
    return list(TOOL_REGISTRY.keys())
