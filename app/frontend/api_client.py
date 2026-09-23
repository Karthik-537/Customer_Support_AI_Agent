"""HTTP client for the FastAPI backend used by the Streamlit frontend."""

import logging
import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ApiClientError(RuntimeError):
    """Raised when the API request fails."""


def _request(method: str, path: str, **kwargs: Any) -> Any:
    """Send a request to the FastAPI backend."""
    url = f"{API_BASE_URL.rstrip('/')}{path}"
    try:
        response = requests.request(method, url, timeout=60, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json()
                message = detail.get("detail", response.text)
            except ValueError:
                message = response.text
            raise ApiClientError(message)
        if response.content:
            try:
                return response.json()
            except ValueError:
                return response.text
        return None
    except requests.RequestException as exc:
        logger.exception("API request failed: %s %s", method, path)
        raise ApiClientError(f"Backend request failed: {exc}") from exc


def get_customers() -> list[dict[str, Any]]:
    """Return all customers available to the frontend demo selector."""
    return _request("GET", "/api/customers")


def create_conversation(user_id: int, title: str = "New Conversation") -> dict[str, Any]:
    """Create a new conversation for a customer."""
    return _request("POST", "/api/conversations", json={"user_id": user_id, "title": title})


def get_conversation(conversation_id: str) -> dict[str, Any]:
    """Fetch a specific conversation's metadata."""
    return _request("GET", f"/api/conversations/{conversation_id}")


def get_conversations(user_id: int) -> list[dict[str, Any]]:
    """Return all conversations for the selected customer."""
    result = _request("GET", f"/api/users/{user_id}/conversations")
    return result.get("conversations", [])


def get_messages(conversation_id: str) -> list[dict[str, Any]]:
    """Return all messages for a conversation."""
    result = _request("GET", f"/api/conversations/{conversation_id}/messages")
    return result.get("messages", [])


def send_message(user_id: int, message: str, conversation_id: Optional[str] = None) -> dict[str, Any]:
    """Send a user message to the backend agent."""
    payload = {"user_id": user_id, "message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return _request("POST", "/api/chat", json=payload)


def rename_conversation(conversation_id: str, user_id: int, title: str) -> dict[str, Any]:
    """Rename a conversation."""
    return _request("PATCH", f"/api/conversations/{conversation_id}", json={"user_id": user_id, "title": title})


def delete_conversation(conversation_id: str, user_id: int) -> dict[str, Any]:
    """Delete a conversation."""
    return _request("DELETE", f"/api/conversations/{conversation_id}", params={"user_id": user_id})
