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
                "name": "get_my_orders",
                "description": "Return all orders for the current customer in a customer-friendly format without exposing internal database identifiers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Internal application customer ID for the customer whose orders should be retrieved"
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_orders_by_product_name",
                "description": "Search all orders for a customer using a product name, supporting case-insensitive and partial matching. Returns every matching order instead of a single order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Internal application customer ID for the customer whose orders are being searched"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Product name or partial product name to match against the customer's order history"
                        }
                    },
                    "required": ["customer_id", "product_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_details",
                "description": "Internal exact lookup for a specific order using its internal UUID. Use this only after the target order has been identified by a customer-safe search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "Internal UUID for the exact order to inspect"
                        }
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "Get the exact status and delivery information for a specific order using its internal UUID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "Internal UUID of the order whose status should be checked"
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
                "description": "Cancel a specific order by internal UUID. This action is only allowed when the order is in PENDING or CONFIRMED status. It must not be used when multiple matching orders exist without customer clarification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "Internal UUID of the order to cancel"
                        }
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_inventory_by_name",
                "description": "Search inventory by a product name, supporting case-insensitive and partial matching. Returns all relevant products instead of a single product.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "Product name or partial product name to search for in inventory"
                        }
                    },
                    "required": ["product_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_inventory",
                "description": "Internal exact inventory lookup by product identifier. Use only after a product has been identified or when a precise internal lookup is needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Internal product identifier used for exact inventory lookup"
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
                "description": "Create a support ticket for a customer. The ticket will be created with OPEN status and the system will keep the customer relationship internal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Internal application customer ID for the customer creating the ticket"
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
                "description": "Get the current status and details of a specific support ticket using its internal ticket ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "Internal UUID for the ticket whose status is requested"
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
                            "type": "string",
                            "description": "Internal application customer ID to escalate"
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for escalation"
                        }
                    },
                    "required": ["customer_id", "reason"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "retrieve_company_knowledge",
                "description": "Retrieve company policy information from the knowledge base. Use this for questions about refund policies, shipping policies, cancellation policies, warranty, FAQs, and other documented company rules.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant company policy information"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
