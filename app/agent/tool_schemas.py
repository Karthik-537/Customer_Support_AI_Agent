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
                "name": "check_order_cancellation",
                "description": "Check whether the customer's matching order(s) are eligible for \
                cancellation based on their current status. This is a read-only operation and \
                does not modify the database.",
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
                        },
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_product_by_name",
                "description": "Search for products by name using case-insensitive and partial matching to determine their current stock availability. Returns all matching products and their stock quantities.",
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
                "name": "create_support_ticket",
                "description": (
                    "Create a support ticket for a customer using the customer's "
                    "product-name match to the relevant order. If multiple matching "
                    "orders exist, the tool must ask for clarification instead of "
                    "creating a ticket automatically. If the customer identifies "
                    "the specific order by its order date, use order_date to select "
                    "that order."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": (
                                "Internal application customer ID for the customer "
                                "creating the ticket"
                            )
                        },
                        "product_name": {
                            "type": "string",
                            "description": (
                                "Optional product name associated with the support issue. "
                                "Provide it when the issue is related to a specific product or order; "
                                "omit it for general, account, billing, or other non-product issues."
                            )
                        },
                        "order_date": {
                            "type": "string",
                            "description": (
                                "Optional order date used to identify the specific "
                                "order when multiple orders exist for the same "
                                "product. Provide the date only when needed to "
                                "disambiguate multiple matching orders."
                                "Format: YYYY-MM-DD"
                            )
                        },
                        "issue": {
                            "type": "string",
                            "description": "The description of the issue"
                        },
                        "priority": {
                            "type": "string",
                            "description": (
                                "Priority of the support ticket based on the urgency and severity "
                                "of the customer's issue. Use LOW for minor or non-urgent issues, "
                                "MEDIUM for normal issues that require standard support, "
                                "HIGH for serious issues that require prompt attention, and "
                                "CRITICAL only for severe issues requiring immediate attention. "
                                "Do not choose a higher priority solely because the customer "
                                "requests it. Default to MEDIUM when the severity is unclear."
                            ),
                            "enum": [
                                "LOW",
                                "MEDIUM",
                                "HIGH",
                                "CRITICAL"
                            ]
                        }
                    },
                    "required": [
                        "customer_id",
                        "product_name",
                        "issue"
                    ]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_support_tickets_by_product_name",
                "description": "Return all support tickets for the current customer associated with a product name, using customer-only and product-name matching rules.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Internal application customer ID for the owner of the tickets"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Product name or partial product name to match against associated support tickets"
                        }
                    },
                    "required": ["customer_id", "product_name"]
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
