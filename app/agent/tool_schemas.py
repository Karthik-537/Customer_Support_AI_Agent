"""Tool schemas for LLM function calling.

This module defines the tool schemas that describe the available functions
to the LLM in a format it can understand.
"""

from typing import Any, Dict, List


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for the customer support agent.

    Returns:
        List of tool definitions for function calling.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "Get the current status and delivery information for a customer order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "The ID of the order"
                        }
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_order",
                "description": "Cancel an order. Orders can only be cancelled if they are in PENDING or CONFIRMED status. SHIPPED, DELIVERED, or already CANCELLED orders cannot be cancelled.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "The ID of the order to cancel"
                        }
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_inventory",
                "description": "Check whether a product is currently available in stock. Returns product details including stock quantity and price.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "The ID of the product to check"
                        }
                    },
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_support_ticket",
                "description": "Create a support ticket for a customer. The ticket will be created with OPEN status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "The ID of the customer creating the ticket"
                        },
                        "issue": {
                            "type": "string",
                            "description": "The description of the issue"
                        },
                        "priority": {
                            "type": "string",
                            "description": "The priority level (LOW, MEDIUM, HIGH, CRITICAL). Defaults to MEDIUM.",
                            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                        }
                    },
                    "required": ["customer_id", "issue"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_ticket_status",
                "description": "Get the current status and details of a support ticket.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "integer",
                            "description": "The ID of the ticket"
                        }
                    },
                    "required": ["ticket_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "escalate_to_human",
                "description": "Escalate a customer issue to a human support representative. Creates a support ticket with HIGH priority and ESCALATED status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "The ID of the customer to escalate"
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for escalation"
                        }
                    },
                    "required": ["customer_id", "reason"]
                }
            }
        }
    ]
