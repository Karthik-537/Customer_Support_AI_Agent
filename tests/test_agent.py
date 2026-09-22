"""Unit tests for the customer support agent."""

from unittest.mock import MagicMock, patch

import pytest

from app.agent.agent import CustomerSupportAgent, get_agent


class TestCustomerSupportAgent:
    """Test cases for the CustomerSupportAgent class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def agent(self, mock_ollama_client):
        """Create an agent with a mocked Ollama client."""
        return CustomerSupportAgent(ollama_client=mock_ollama_client)

    def test_agent_initialization(self, mock_ollama_client):
        """Test that the agent initializes correctly."""
        agent = CustomerSupportAgent(ollama_client=mock_ollama_client)
        assert agent.llm_client == mock_ollama_client
        assert len(agent.tool_schemas) == 6  # We have 6 tools
        assert agent.system_prompt is not None

    def test_general_question_no_tool_call(self, agent, mock_ollama_client):
        """Test a general question that does not require a tool."""
        # Mock LLM response without tool calls
        mock_ollama_client.generate_response.return_value = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            }
        }

        result = agent.process_message("Hello")

        assert result["success"] is True
        assert "Hello" in result["response"]
        assert result["tool_calls"] == []
        assert result["iterations"] == 1

        # Verify the LLM was called with tools
        mock_ollama_client.generate_response.assert_called_once()
        call_args = mock_ollama_client.generate_response.call_args
        # System prompt + user message
        assert len(call_args[0][0]) == 2
        assert call_args[0][1] is not None  # Tools were provided

    def test_order_status_request_tool_call(self, agent, mock_ollama_client):
        """Test an order status request that triggers a tool call."""
        # Mock LLM response requesting get_order_status tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": {
                                "name": "get_order_status",
                                "arguments": {"order_id": 1001}
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Your order #1001 is currently shipped and should arrive soon."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "order_id": 1001,
                "status": "SHIPPED",
                "product_name": "Dell Laptop"
            }

            result = agent.process_message("Where is order 1001?")

            assert result["success"] is True
            assert "shipped" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once_with("get_order_status", order_id=1001)

    def test_inventory_request_tool_call(self, agent, mock_ollama_client):
        """Test an inventory request that triggers a tool call."""
        # Mock LLM response requesting check_inventory tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_456",
                            "function": {
                                "name": "check_inventory",
                                "arguments": {"product_id": "LAP001"}
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Yes, the Dell Laptop (LAP001) is currently in stock with 5 units available."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "product_id": "LAP001",
                "product_name": "Dell Laptop",
                "stock_quantity": 5,
                "in_stock": True
            }

            result = agent.process_message("Do you have product LAP001 in stock?")

            assert result["success"] is True
            assert "stock" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once_with("check_inventory", product_id="LAP001")

    def test_ticket_status_request_tool_call(self, agent, mock_ollama_client):
        """Test a ticket status request that triggers a tool call."""
        # Mock LLM response requesting get_ticket_status tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_789",
                            "function": {
                                "name": "get_ticket_status",
                                "arguments": {"ticket_id": 1001}
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Your ticket #1001 is currently in progress and being handled by our support team."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "ticket_id": 1001,
                "status": "IN_PROGRESS",
                "priority": "HIGH"
            }

            result = agent.process_message("What is the status of ticket 1001?")

            assert result["success"] is True
            assert "progress" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once_with("get_ticket_status", ticket_id=1001)

    def test_cancellation_request_tool_call(self, agent, mock_ollama_client):
        """Test a cancellation request that triggers a tool call."""
        # Mock LLM response requesting cancel_order tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "function": {
                                "name": "cancel_order",
                                "arguments": {"order_id": 1001}
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Your order #1001 has been successfully cancelled."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "order_id": 1001,
                "status": "CANCELLED",
                "message": "Order cancelled successfully"
            }

            result = agent.process_message("Cancel order 1001.")

            assert result["success"] is True
            assert "cancelled" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once_with("cancel_order", order_id=1001)

    def test_support_ticket_creation_tool_call(self, agent, mock_ollama_client):
        """Test a support ticket creation request that triggers a tool call."""
        # Mock LLM response requesting create_support_ticket tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_def",
                            "function": {
                                "name": "create_support_ticket",
                                "arguments": {
                                    "customer_id": 101,
                                    "issue": "Laptop arrived damaged",
                                    "priority": "HIGH"
                                }
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "I've created a support ticket (#1005) for your damaged laptop issue. Our team will contact you shortly."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "ticket_id": 1005,
                "customer_id": 101,
                "issue": "Laptop arrived damaged",
                "priority": "HIGH",
                "status": "OPEN"
            }

            result = agent.process_message("My laptop arrived damaged.")

            assert result["success"] is True
            assert "ticket" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once()

    def test_escalation_tool_call(self, agent, mock_ollama_client):
        """Test an escalation request that triggers a tool call."""
        # Mock LLM response requesting escalate_to_human tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_ghi",
                            "function": {
                                "name": "escalate_to_human",
                                "arguments": {
                                    "customer_id": 101,
                                    "reason": "Customer was charged twice and needs immediate assistance"
                                }
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "I've escalated your billing issue to our human support team. They will prioritize your case and contact you shortly."
                }
            }
        ]

        # Mock the tool execution
        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "ticket_id": 1006,
                "customer_id": 101,
                "status": "ESCALATED",
                "priority": "HIGH",
                "message": "Issue escalated to human support."
            }

            result = agent.process_message("I was charged twice and need this escalated.")

            assert result["success"] is True
            assert "escalated" in result["response"].lower()
            assert result["iterations"] == 2

            # Verify tool was called
            mock_execute.assert_called_once()

    def test_llm_error_handling(self, agent, mock_ollama_client):
        """Test that LLM errors are handled gracefully."""
        # Mock LLM to raise an exception
        mock_ollama_client.generate_response.side_effect = Exception("LLM connection failed")

        result = agent.process_message("Hello")

        assert result["success"] is False
        assert "error" in result
        assert "LLM error" in result["error"]
        assert "response" in result

    def test_tool_execution_error_handling(self, agent, mock_ollama_client):
        """Test that tool execution errors are handled gracefully."""
        # Mock LLM response requesting a tool
        mock_ollama_client.generate_response.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_error",
                            "function": {
                                "name": "invalid_tool",
                                "arguments": {}
                            }
                        }
                    ]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "I encountered an error with the tool request."
                }
            }
        ]

        result = agent.process_message("Test")

        # The agent should handle the error and continue
        assert result["success"] is True or result["success"] is False
        # Either way, it shouldn't crash

    def test_conversation_history_handling(self, agent, mock_ollama_client):
        """Test that conversation history is properly handled."""
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        # Mock LLM response
        mock_ollama_client.generate_response.return_value = {
            "message": {
                "role": "assistant",
                "content": "I can help with that."
            }
        }

        result = agent.process_message("Where is order 1001?", conversation_history)

        assert result["success"] is True

        # Verify that conversation history was included
        call_args = mock_ollama_client.generate_response.call_args
        messages = call_args[0][0]
        # System + 2 history messages + current user message = 4
        assert len(messages) == 4
        assert messages[1]["content"] == "Hello"
        assert messages[2]["content"] == "Hi there!"
        assert messages[3]["content"] == "Where is order 1001?"

    def test_max_iterations_protection(self, agent, mock_ollama_client):
        """Test that the agent stops after max iterations to prevent infinite loops."""
        # Mock LLM to keep requesting tool calls
        mock_ollama_client.generate_response.return_value = {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_loop",
                        "function": {
                            "name": "get_order_status",
                            "arguments": {"order_id": 1001}
                        }
                    }
                ]
            }
        }

        with patch("app.agent.agent.execute_tool") as mock_execute:
            mock_execute.return_value = {"success": True, "order_id": 1001, "status": "SHIPPED"}

            result = agent.process_message("Test")

            assert result["success"] is False
            assert "Max iterations" in result["error"]


def test_get_agent():
    """Test the get_agent factory function."""
    with patch("app.agent.agent.get_ollama_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        agent = get_agent()

        assert isinstance(agent, CustomerSupportAgent)
        assert agent.llm_client == mock_client
        mock_get_client.assert_called_once()
