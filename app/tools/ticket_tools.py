"""Support ticket creation and query tools.

This module provides functions to create and query support tickets in SQLite.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Customer, SupportTicket, TicketPriority, TicketStatus


def create_support_ticket(customer_id: int, issue: str, priority: str = "MEDIUM") -> dict[str, Any]:
    """Create a support ticket for a customer.

    Validates that the customer exists before creating the ticket.

    Args:
        customer_id: The ID of the customer creating the ticket.
        issue: The description of the issue.
        priority: The priority level (LOW, MEDIUM, HIGH, CRITICAL). Defaults to MEDIUM.

    Returns:
        If successful:
        {
            "success": true,
            "ticket_id": int,
            "customer_id": int,
            "issue": str,
            "priority": str,
            "status": str
        }

        If the customer does not exist:
        {
            "success": false,
            "error": "Customer not found"
        }

        If the priority is invalid:
        {
            "success": false,
            "error": "Invalid priority"
        }
    """
    # Validate priority
    try:
        priority_enum = TicketPriority(priority.upper())
    except ValueError:
        return {"success": False, "error": "Invalid priority"}

    db: Session = SessionLocal()
    try:
        # Verify customer exists
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            return {"success": False, "error": "Customer not found"}

        # Create the ticket
        ticket = SupportTicket(
            customer_id=customer_id,
            issue=issue,
            priority=priority_enum,
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "success": True,
            "ticket_id": ticket.id,
            "customer_id": ticket.customer_id,
            "issue": ticket.issue,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def get_ticket_status(ticket_id: int) -> dict[str, Any]:
    """Retrieve ticket information by ticket ID.

    Args:
        ticket_id: The ID of the ticket to retrieve.

    Returns:
        A dictionary containing ticket information if found:
        {
            "success": true,
            "ticket_id": int,
            "customer_id": int,
            "issue": str,
            "priority": str,
            "status": str,
            "created_at": str,
            "updated_at": str
        }

        If the ticket does not exist:
        {
            "success": false,
            "error": "Ticket not found"
        }
    """
    db: Session = SessionLocal()
    try:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket is None:
            return {"success": False, "error": "Ticket not found"}

        return {
            "success": True,
            "ticket_id": ticket.id,
            "customer_id": ticket.customer_id,
            "issue": ticket.issue,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()
