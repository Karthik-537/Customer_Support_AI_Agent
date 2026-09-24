"""Human escalation tools.

This module provides functions to escalate customer issues to human support.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Customer, SupportTicket, TicketPriority, TicketStatus


def escalate_to_human(customer_id: int, reason: str) -> dict[str, Any]:
    """Escalate a customer issue to a human support representative.

    Creates a support ticket with HIGH priority and ESCALATED status.

    Args:
        customer_id: The ID of the customer to escalate.
        reason: The reason for escalation (stored as the issue).

    Returns:
        If successful:
        {
            "success": true,
            "ticket_id": int,
            "customer_id": int,
            "status": "ESCALATED",
            "priority": "HIGH",
            "message": "Issue escalated to human support."
        }

        If the customer does not exist:
        {
            "success": false,
            "error": "Customer not found"
        }
    """
    db: Session = SessionLocal()
    try:
        # Verify customer exists
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            return {"success": False, "error": "Customer not found"}

        # Create escalated ticket
        ticket = SupportTicket(
            customer_id=customer_id,
            issue=reason,
            priority=TicketPriority.HIGH.value,
            status=TicketStatus.ESCALATED.value,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "success": True,
            "ticket_id": ticket.id,
            "customer_id": ticket.customer_id,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "message": "Issue escalated to human support.",
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()
