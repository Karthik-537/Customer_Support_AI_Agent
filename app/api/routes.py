"""FastAPI routes for the customer support agent."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agent.agent import get_agent
from app.auth.dependencies import get_current_customer
from app.auth.service import login_customer_account, register_customer_account
from app.database.db import SessionLocal
from app.database.models import Customer
from app.memory.conversation_memory import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_messages,
    list_user_conversations,
    update_conversation,
)
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    ConversationsListResponse,
    CustomerSummary,
    HealthResponse,
    LoginRequest,
    MessageRecord,
    MessagesResponse,
    RegisterRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _ensure_conversation_owned(conversation_id: str, user_id: str) -> dict[str, Any]:
    """Validate that the conversation exists and belongs to the requested user."""
    conv = get_conversation(conversation_id)
    if not conv.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not own this conversation")
    return conv


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Basic API health check."""
    return HealthResponse(status="ok")


@router.post("/auth/register", response_model=CustomerSummary)
def register_customer(payload: RegisterRequest) -> CustomerSummary:
    """Register a new customer account using email and password."""
    return register_customer_account(payload)


@router.post("/auth/login", response_model=TokenResponse)
def login_customer(payload: LoginRequest) -> TokenResponse:
    """Authenticate a customer by email and password and return a JWT."""
    return login_customer_account(payload)


@router.get("/auth/me", response_model=CustomerSummary)
def get_me(current_customer: Customer = Depends(get_current_customer)) -> CustomerSummary:
    """Return the authenticated customer's safe public profile."""
    return CustomerSummary(id=current_customer.id, name=current_customer.name, email=current_customer.email)


@router.get("/customers", response_model=list[CustomerSummary])
def get_customers() -> list[CustomerSummary]:
    """Return the customer list for the frontend demo selector."""
    db = SessionLocal()
    try:
        customers = db.query(Customer).order_by(Customer.id).all()
        return [
            CustomerSummary(id=c.id, name=c.name, email=c.email)
            for c in customers
        ]
    except Exception as exc:
        logger.exception("Failed to load customers")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load customers") from exc
    finally:
        db.close()


@router.post("/conversations", response_model=ConversationResponse)
def create_new_conversation(payload: ConversationCreateRequest, current_customer: Customer = Depends(get_current_customer)) -> ConversationResponse:
    """Create a new conversation for the authenticated customer."""
    user_id = payload.user_id or current_customer.id
    if user_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create conversation for another customer")
    try:
        result = create_conversation(user_id, title=payload.title or "New Conversation")
    except Exception as exc:
        logger.exception("Failed to create conversation")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create conversation") from exc

    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("error", "Could not create conversation"))

    return ConversationResponse(
        success=True,
        conversation_id=result["conversation_id"],
        id=result.get("id"),
        user_id=user_id,
        title=result.get("title"),
        created_at=result.get("created_at"),
        updated_at=result.get("created_at"),
        is_deleted=result.get("is_deleted", False),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation_by_id(conversation_id: str, current_customer: Customer = Depends(get_current_customer)) -> ConversationResponse:
    """Return metadata for a specific conversation."""
    result = get_conversation(conversation_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if result.get("user_id") != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this conversation")

    return ConversationResponse(
        success=True,
        conversation_id=result["conversation_id"],
        id=result.get("id"),
        user_id=result.get("user_id"),
        title=result.get("title"),
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        is_deleted=result.get("is_deleted", False),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
def get_conversation_messages(conversation_id: str, current_customer: Customer = Depends(get_current_customer)) -> MessagesResponse:
    """Return the complete message history for a conversation."""
    result = get_messages(conversation_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conversation = get_conversation(conversation_id)
    if conversation.get("user_id") != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this conversation")

    return MessagesResponse(
        success=True,
        conversation_id=conversation_id,
        messages=[
            MessageRecord(
                id=item["id"],
                user_message=item["user_message"],
                response=item["response"],
                created_at=item["created_at"],
            )
            for item in result.get("messages", [])
        ],
    )


@router.get("/users/{user_id}/conversations", response_model=ConversationsListResponse)
def list_conversations_for_user(user_id: str, current_customer: Customer = Depends(get_current_customer)) -> ConversationsListResponse:
    """Return all conversations for the authenticated customer."""
    if user_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own conversations")

    result = list_user_conversations(user_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("error", "Could not load conversations"))

    return ConversationsListResponse(
        success=True,
        user_id=user_id,
        conversations=[
            ConversationResponse(
                success=True,
                conversation_id=item["conversation_id"],
                id=item.get("id"),
                user_id=user_id,
                title=item.get("title"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
                is_deleted=item.get("is_deleted", False),
            )
            for item in result.get("conversations", [])
        ],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation_metadata(conversation_id: str, payload: ConversationUpdateRequest, current_customer: Customer = Depends(get_current_customer)) -> ConversationResponse:
    """Rename or update a conversation's metadata."""
    conversation = get_conversation(conversation_id)
    if not conversation.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.get("user_id") != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this conversation")

    result = update_conversation(conversation_id, title=payload.title)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("error", "Could not update conversation"))

    return ConversationResponse(
        success=True,
        conversation_id=result["conversation_id"],
        user_id=current_customer.id,
        title=result.get("title"),
        updated_at=result.get("updated_at"),
        is_deleted=result.get("is_deleted", False),
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation_by_id(conversation_id: str, user_id: Optional[str] = Query(None, description="Customer ID that owns the conversation"), current_customer: Customer = Depends(get_current_customer)) -> dict[str, Any]:
    """Delete a conversation and its messages."""
    target_user_id = user_id or current_customer.id
    if target_user_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own conversations")
    conversation = get_conversation(conversation_id)
    if not conversation.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.get("user_id") != current_customer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this conversation")

    result = delete_conversation(conversation_id)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("error", "Could not delete conversation"))

    return {
        "success": True,
        "conversation_id": conversation_id,
        "is_deleted": result.get("is_deleted", True),
    }


@router.post("/chat", response_model=ChatResponse)
def chat_with_agent(payload: ChatRequest, current_customer: Customer = Depends(get_current_customer)) -> ChatResponse:
    """Send a customer message to the existing agent service using JWT identity."""
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required")

    customer_id = current_customer.id
    conversation_id = payload.conversation_id
    if conversation_id:
        existing = get_conversation(conversation_id)
        if not existing.get("success"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if existing.get("user_id") != customer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this conversation")
    else:
        created_conversation = create_conversation(customer_id, title="New Conversation")
        if not created_conversation.get("success"):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=created_conversation.get("error", "Could not create conversation"))
        conversation_id = created_conversation["conversation_id"]

    agent = get_agent()
    try:
        result = agent.process_message(
            user_message=payload.message,
            user_id=customer_id,
            conversation_id=conversation_id,
        )
    except Exception as exc:
        logger.exception("Agent request failed for chat route")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sorry, I couldn't process your request right now.") from exc

    if not result.get("success"):
        detail = result.get("response") or result.get("error") or "Could not process request"
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

    return ChatResponse(conversation_id=conversation_id, response=result["response"])
