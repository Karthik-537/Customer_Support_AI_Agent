"""Support ticket creation and query tools.

This module provides functions to create and query support tickets in SQLite.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Customer, SupportTicket, TicketPriority, TicketStatus


def _build_ticket_reference(ticket_id: str) -> str:
    """Generate a customer-safe ticket reference."""
    return f"TKT-{str(ticket_id)[:8].upper()}" if ticket_id else "TKT-UNKNOWN"


def create_support_ticket(customer_id: str, issue: str, priority: str = "MEDIUM") -> dict[str, Any]:
    """Create a support ticket for a customer with internal UUID handling."""
    try:
        priority_enum = TicketPriority(priority.upper())
    except ValueError:
        return {"success": False, "error": "Invalid priority"}

    db: Session = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            return {"success": False, "error": "Customer not found"}

        ticket = SupportTicket(
            customer_id=customer_id,
            issue=issue,
            priority=priority_enum,
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        ticket_ref = _build_ticket_reference(ticket.id)
        return {
            "success": True,
            "ticket_id": ticket.id,
            "ticket_reference": ticket_ref,
            "customer_id": ticket.customer_id,
            "issue": ticket.issue,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_ticket_status(ticket_id: str) -> dict[str, Any]:
    """Retrieve ticket information by internal ticket ID."""
    db: Session = SessionLocal()
    try:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket is None:
            return {"success": False, "error": "Ticket not found"}

        return {
            "success": True,
            "ticket_id": ticket.id,
            "ticket_reference": _build_ticket_reference(ticket.id),
            "customer_id": ticket.customer_id,
            "issue": ticket.issue,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()
