"""Conversation memory service for SQLite persistence.

This module handles short-term/conversation memory storage and retrieval.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Conversation, Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    return str(uuid.uuid4())


def create_conversation(
    user_id: int,
    title: str = "New Conversation",
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new conversation.

    Args:
        user_id: The ID of the customer.
        title: Optional title for the conversation.
        conversation_id: Optional pre-generated conversation ID.

    Returns:
        Dictionary containing the created conversation info.
    """
    db: Session = SessionLocal()
    try:
        conv_id = conversation_id or generate_conversation_id()

        conversation = Conversation(
            conversation_id=conv_id,
            user_id=user_id,
            title=title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        logger.info(f"Created conversation {conv_id} for user {user_id}")
        return {
            "success": True,
            "conversation_id": conversation.conversation_id,
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Get a conversation by conversation_id.

    Args:
        conversation_id: The conversation ID to retrieve.

    Returns:
        Dictionary containing conversation info or error.
    """
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        ).first()

        if conversation is None:
            return {"success": False, "error": "Conversation not found"}

        return {
            "success": True,
            "conversation_id": conversation.conversation_id,
            "id": conversation.id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "is_deleted": conversation.is_deleted,
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def get_or_create_conversation(
    user_id: int,
    conversation_id: Optional[str] = None,
    title: str = "New Conversation"
) -> Dict[str, Any]:
    """Get an existing conversation or create a new one.

    Args:
        user_id: The ID of the customer.
        conversation_id: Optional conversation ID to retrieve.
        title: Title for new conversation if created.

    Returns:
        Dictionary containing conversation info.
    """
    if conversation_id:
        result = get_conversation(conversation_id)
        if result["success"]:
            # Verify ownership
            if result["user_id"] == user_id:
                return result
            else:
                return {"success": False, "error": "Conversation does not belong to user"}

    # Create new conversation
    return create_conversation(user_id, title)


def add_conversation_message(
    conversation_id: str,
    user_message: str,
    response: str,
) -> Dict[str, Any]:
    """Add one user/assistant exchange to a conversation.

    Args:
        conversation_id: The conversation ID.
        user_message: The customer's message.
        response: The assistant's response.

    Returns:
        Dictionary containing the created message info.
    """
    db: Session = SessionLocal()
    try:
        # Verify conversation exists
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        ).first()

        if conversation is None:
            return {"success": False, "error": "Conversation not found"}

        message = Message(
            conversation_id=conversation_id,
            user_message=user_message,
            response=response,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Added exchange to conversation {conversation_id}")
        return {
            "success": True,
            "message_id": message.id,
            "conversation_id": conversation_id,
            "user_message": message.user_message,
            "response": message.response,
            "created_at": message.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding message: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def get_messages(
    conversation_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Get messages from a conversation.

    Args:
        conversation_id: The conversation ID.
        limit: Optional limit on number of messages.

    Returns:
        Dictionary containing messages list.
    """
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        ).first()
        if conversation is None:
            return {"success": False, "error": "Conversation not found"}

        query = db.query(Message).filter(
            Message.conversation_id == conversation.conversation_id,
        ).order_by(Message.created_at)

        if limit:
            query = query.limit(limit)

        messages = query.all()

        return {
            "success": True,
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "user_message": msg.user_message,
                    "response": msg.response,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def get_recent_messages(
    conversation_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent messages from a conversation.

    Args:
        conversation_id: The conversation ID.
        limit: Maximum number of recent messages.

    Returns:
        List of message dictionaries.
    """
    result = get_messages(conversation_id, limit=limit)
    if result["success"]:
        return result["messages"]
    return []


def update_conversation(
    conversation_id: str,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """Update conversation metadata.

    Args:
        conversation_id: The conversation ID.
        title: New title for the conversation.

    Returns:
        Dictionary containing updated conversation info.
    """
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        ).first()

        if conversation is None:
            return {"success": False, "error": "Conversation not found"}

        if title is not None:
            conversation.title = title

        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(conversation)

        logger.info(f"Updated conversation {conversation_id}")
        return {
            "success": True,
            "conversation_id": conversation.conversation_id,
            "title": conversation.title,
            "updated_at": conversation.updated_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating conversation: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def delete_conversation(conversation_id: str) -> Dict[str, Any]:
    """Delete a conversation and all its messages.

    Args:
        conversation_id: The conversation ID.

    Returns:
        Dictionary indicating success/failure.
    """
    db: Session = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        ).first()

        if conversation is None:
            return {"success": False, "error": "Conversation not found"}

        conversation.is_deleted = True
        db.commit()

        logger.info(f"Soft-deleted conversation {conversation_id}")
        return {"success": True, "conversation_id": conversation_id, "is_deleted": True}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def list_user_conversations(user_id: int) -> Dict[str, Any]:
    """List all conversations for a user.

    Args:
        user_id: The ID of the customer.

    Returns:
        Dictionary containing list of conversations.
    """
    db: Session = SessionLocal()
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.is_deleted.is_(False),
        ).order_by(Conversation.updated_at.desc()).all()

        return {
            "success": True,
            "user_id": user_id,
            "conversations": [
                {
                    "id": conv.id,
                    "conversation_id": conv.conversation_id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "is_deleted": conv.is_deleted,
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()
