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


def _request(method: str, path: str, token: Optional[str] = None, **kwargs: Any) -> Any:
    """Send a request to the FastAPI backend."""
    url = f"{API_BASE_URL.rstrip('/')}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers
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


def register_customer(name: str, email: str, password: str) -> dict[str, Any]:
    """Register a new customer account."""
    return _request("POST", "/api/auth/register", json={"name": name, "email": email, "password": password})


def login_customer(email: str, password: str) -> dict[str, Any]:
    """Log in a customer and return the JWT token payload."""
    return _request("POST", "/api/auth/login", json={"email": email, "password": password})


def get_current_customer(token: str) -> dict[str, Any]:
    """Return the authenticated customer profile."""
    return _request("GET", "/api/auth/me", token=token)


def get_customers() -> list[dict[str, Any]]:
    """Return all customers available to the frontend demo selector."""
    return _request("GET", "/api/customers")


def create_conversation(user_id: str, title: str = "New Conversation", token: Optional[str] = None) -> dict[str, Any]:
    """Create a new conversation for a customer."""
    payload = {"title": title}
    if user_id is not None:
        payload["user_id"] = user_id
    return _request("POST", "/api/conversations", token=token, json=payload)


def get_conversation(conversation_id: str, token: Optional[str] = None) -> dict[str, Any]:
    """Fetch a specific conversation's metadata."""
    return _request("GET", f"/api/conversations/{conversation_id}", token=token)


def get_conversations(user_id: str, token: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all conversations for the selected customer."""
    result = _request("GET", f"/api/users/{user_id}/conversations", token=token)
    return result.get("conversations", [])


def get_messages(conversation_id: str, token: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all messages for a conversation."""
    result = _request("GET", f"/api/conversations/{conversation_id}/messages", token=token)
    return result.get("messages", [])


def send_message(user_id: Optional[str], message: str, conversation_id: Optional[str] = None, token: Optional[str] = None) -> dict[str, Any]:
    """Send a user message to the backend agent."""
    payload: dict[str, Any] = {"message": message}
    if user_id is not None:
        payload["user_id"] = user_id
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return _request("POST", "/api/chat", token=token, json=payload)


def rename_conversation(conversation_id: str, user_id: Optional[str], title: str, token: Optional[str] = None) -> dict[str, Any]:
    """Rename a conversation."""
    payload = {"title": title}
    if user_id is not None:
        payload["user_id"] = user_id
    return _request("PATCH", f"/api/conversations/{conversation_id}", token=token, json=payload)


def delete_conversation(conversation_id: str, user_id: Optional[str] = None, token: Optional[str] = None) -> dict[str, Any]:
    """Delete a conversation."""
    params = {}
    if user_id is not None:
        params["user_id"] = user_id
    return _request("DELETE", f"/api/conversations/{conversation_id}", token=token, params=params)
