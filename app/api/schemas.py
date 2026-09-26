"""Pydantic schemas for the FastAPI layer."""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for a chat interaction."""

    user_id: str = Field(..., description="Internal customer ID that owns the conversation")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID for continuing a chat")
    message: str = Field(..., min_length=1, description="Message sent by the customer")


class ChatResponse(BaseModel):
    """Response payload after a chat request is processed."""

    conversation_id: str
    response: str


class CustomerSummary(BaseModel):
    """Customer data returned to the frontend."""

    id: str
    name: str
    email: str


class ConversationCreateRequest(BaseModel):
    """Request payload for creating a customer conversation."""

    user_id: str
    title: Optional[str] = "New Conversation"


class ConversationResponse(BaseModel):
    """Conversation metadata."""

    success: bool
    conversation_id: str
    id: Optional[str] = None
    user_id: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_deleted: bool = False
    error: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    """Request payload for updating a conversation."""

    user_id: str
    title: Optional[str] = None


class MessageRecord(BaseModel):
    """Single user/assistant exchange in a conversation."""

    id: str
    user_message: str
    response: str
    created_at: str


class MessagesResponse(BaseModel):
    """Messages payload for a conversation."""

    success: bool
    conversation_id: str
    messages: list[MessageRecord] = []
    error: Optional[str] = None


class ConversationsListResponse(BaseModel):
    """List of conversations for a user."""

    success: bool
    user_id: str
    conversations: list[ConversationResponse] = []
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
