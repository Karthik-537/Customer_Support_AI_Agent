"""Manual test script for the customer support agent.

This script allows you to interact with the real agent using Ollama.
Run this script to test the agent with actual LLM responses.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.agent.agent import get_agent


def main():
    """Run the manual agent test."""
    print("=" * 60)
    print("Customer Support AI Agent - Manual Test")
    print("=" * 60)
    print()

    try:
        agent = get_agent()
        print("Agent initialized successfully!")
        print(f"Available tools: {', '.join(agent.tool_schemas[i]['function']['name'] for i in range(len(agent.tool_schemas)))}")
        print()
    except Exception as e:
        print(f"Error initializing agent: {e}")
        print("Make sure Ollama is running and the qwen3:8b model is available.")
        return

    conversation_history = []

    print("Type 'quit' or 'exit' to end the session.")
    print()

    while True:
        try:
            user_input = input("User: ").strip()

            if user_input.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print()
            print("Processing...")
            print()

            result = agent.process_message(user_input, conversation_history)

            if result["success"]:
                print(f"Agent: {result['response']}")
                print()

                # Add to conversation history
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": result['response']})

                # Show tool call information if available
                if result.get("iterations", 0) > 1:
                    print(f"(Agent made {result['iterations']} iteration(s) including tool calls)")
                    print()
            else:
                print(f"Agent Error: {result.get('error', 'Unknown error')}")
                print(f"Response: {result.get('response', 'No response')}")
                print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print()


if __name__ == "__main__":
    main()
