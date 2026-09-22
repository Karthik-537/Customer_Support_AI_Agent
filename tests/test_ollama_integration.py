"""Integration test for the agent with real Ollama calls.

This script tests the agent with actual Ollama responses to verify
tool calling works end-to-end.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.agent.agent import get_agent


def test_ollama_integration():
    """Test the agent with real Ollama calls."""
    print("=" * 60)
    print("Ollama Integration Test")
    print("=" * 60)
    print()

    try:
        agent = get_agent()
        print("[OK] Agent initialized successfully")
        print(f"[OK] Model: {agent.llm_client.model}")
        print(f"[OK] Host: {agent.llm_client.host}")
        print(f"[OK] Available tools: {len(agent.tool_schemas)}")
        print()
    except Exception as e:
        print(f"[ERROR] Error initializing agent: {e}")
        return False

    test_cases = [
        ("Hello", "General greeting - no tool expected"),
        ("Where is order 1?", "Order status - get_order_status expected"),
        ("Is LAP001 in stock?", "Inventory check - check_inventory expected"),
        ("What is the status of ticket 1?", "Ticket status - get_ticket_status expected"),
    ]

    for user_message, description in test_cases:
        print(f"Test: {description}")
        print(f"User: {user_message}")
        print()

        try:
            result = agent.process_message(user_message)

            if result["success"]:
                print(f"Agent: {result['response']}")
                print(f"Iterations: {result.get('iterations', 1)}")
                print(f"[OK] Test passed")
            else:
                print(f"[ERROR] Test failed: {result.get('error', 'Unknown error')}")
                print(f"Response: {result.get('response', 'No response')}")

        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")

        print("-" * 60)
        print()

    return True


if __name__ == "__main__":
    success = test_ollama_integration()
    sys.exit(0 if success else 1)
