"""Human escalation tools.

This module provides functions to escalate customer issues to human support.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Customer, SupportTicket, TicketPriority, TicketStatus


def escalate_to_human(customer_id: str, reason: str) -> dict[str, Any]:
    """Escalate a customer issue to a human support representative."""
    db: Session = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            return {"success": False, "error": "Customer not found"}

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
            "ticket_reference": f"TKT-{str(ticket.id)[:8].upper()}",
            "customer_id": ticket.customer_id,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "message": "Issue escalated to human support.",
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()
