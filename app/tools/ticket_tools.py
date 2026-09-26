"""Support ticket creation and query tools.

This module provides functions to create and query support tickets in SQLite.
"""

from __future__ import annotations

from typing import Any, List

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import (
    Customer,
    Order,
    SupportTicket,
    TicketPriority,
    TicketStatus,
)


def _build_ticket_reference(ticket_id: str) -> str:
    """Generate a customer-safe ticket reference."""
    return f"TKT-{str(ticket_id)[:8].upper()}" if ticket_id else "TKT-UNKNOWN"


def _get_matching_customer_orders(
    db: Session,
    customer_id: str,
    product_name: str,
):
    """Find all orders for the customer matching the product name."""

    return (
        db.query(Order)
        .filter(
            Order.customer_id == customer_id,
            Order.product_name.ilike(f"%{product_name}%"),
        )
        .order_by(Order.order_date.desc())
        .all()
    )


def _build_ticket_payload(
    ticket: SupportTicket,
    product_name: str | None = None,
) -> dict[str, Any]:
    """Build a customer-safe ticket response."""

    payload = {
        "ticket_reference": _build_ticket_reference(ticket.id),
        "product_name": product_name,
        "issue": ticket.issue,
        "priority": (
            ticket.priority.value
            if hasattr(ticket.priority, "value")
            else str(ticket.priority)
        ),
        "status": (
            ticket.status.value
            if hasattr(ticket.status, "value")
            else str(ticket.status)
        ),
        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at
            else None
        ),
        "updated_at": (
            ticket.updated_at.isoformat()
            if ticket.updated_at
            else None
        ),
    }

    if ticket.order_id and ticket.order:
        payload["order_status"] = (
            ticket.order.status.value
            if hasattr(ticket.order.status, "value")
            else str(ticket.order.status)
        )

    return payload


def create_support_ticket(
    customer_id: str,
    product_name: str,
    issue: str,
    priority: str = "MEDIUM",
) -> dict[str, Any]:
    """Create a support ticket for a customer's product order."""

    query = (product_name or "").strip()

    if not query:
        return {
            "success": False,
            "error": "Product name is required",
        }

    if not issue or not issue.strip():
        return {
            "success": False,
            "error": "Issue is required",
        }

    try:
        priority_enum = TicketPriority(priority.upper())
    except ValueError:
        return {
            "success": False,
            "error": "Invalid priority",
        }

    db: Session = SessionLocal()

    try:
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id)
            .first()
        )

        if customer is None:
            return {
                "success": False,
                "error": "Customer not found",
            }

        matches = _get_matching_customer_orders(
            db,
            customer_id,
            query,
        )

        if not matches:
            return {
                "success": False,
                "error": "ORDER_NOT_FOUND",
                "product_name": query,
                "message": (
                    "No order was found for this product "
                    "for the current customer."
                ),
            }

        if len(matches) > 1:
            return {
                "success": False,
                "error": "MULTIPLE_MATCHES",
                "product_name": query,
                "matches": [
                    {
                        "product_name": order.product_name,
                        "order_date": (
                            order.order_date.isoformat()
                            if order.order_date
                            else None
                        ),
                        "quantity": order.quantity,
                        "status": (
                            order.status.value
                            if hasattr(order.status, "value")
                            else str(order.status)
                        ),
                        "delivery_date": (
                            order.delivery_date.isoformat()
                            if order.delivery_date
                            else None
                        ),
                    }
                    for order in matches
                ],
                "message": (
                    "Multiple matching orders were found. "
                    "Please identify which order you mean "
                    "before creating the ticket."
                ),
            }

        selected_order = matches[0]

        ticket = SupportTicket(
            customer_id=customer_id,
            order_id=selected_order.id,
            issue=issue.strip(),
            priority=priority_enum,
            status=TicketStatus.OPEN,
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "success": True,
            "ticket_reference": _build_ticket_reference(ticket.id),
            "product_name": selected_order.product_name,
            "issue": ticket.issue,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "created_at": (
                ticket.created_at.isoformat()
                if ticket.created_at
                else None
            ),
            "updated_at": (
                ticket.updated_at.isoformat()
                if ticket.updated_at
                else None
            ),
        }

    except Exception as exc:
        db.rollback()

        return {
            "success": False,
            "error": f"Database error: {str(exc)}",
        }

    finally:
        db.close()


def get_ticket_status(ticket_id: str) -> dict[str, Any]:
    """Retrieve ticket information using the internal ticket ID."""

    db: Session = SessionLocal()

    try:
        ticket = (
            db.query(SupportTicket)
            .filter(SupportTicket.id == ticket_id)
            .first()
        )

        if ticket is None:
            return {
                "success": False,
                "error": "Ticket not found",
            }

        product_name = None

        if ticket.order:
            product_name = ticket.order.product_name

        return {
            "success": True,
            **_build_ticket_payload(
                ticket,
                product_name,
            ),
        }

    except Exception as exc:
        db.rollback()

        return {
            "success": False,
            "error": f"Database error: {str(exc)}",
        }

    finally:
        db.close()


def get_support_tickets_by_product_name(
    customer_id: str,
    product_name: str,
) -> dict[str, Any]:
    """Return all support tickets for the current customer matching a product name."""

    query = (product_name or "").strip()

    if not query:
        return {
            "success": False,
            "error": "Product name is required",
        }

    db: Session = SessionLocal()

    try:
        tickets = (
            db.query(SupportTicket)
            .join(Order, Order.id == SupportTicket.order_id)
            .filter(
                SupportTicket.customer_id == customer_id,
                Order.product_name.ilike(f"%{query}%"),
            )
            .order_by(SupportTicket.created_at.desc())
            .all()
        )

        results = [
            _build_ticket_payload(
                ticket,
                ticket.order.product_name if ticket.order else None,
            )
            for ticket in tickets
        ]

        return {
            "success": True,
            "count": len(results),
            "tickets": results,
        }

    except Exception as exc:
        db.rollback()

        return {
            "success": False,
            "error": f"Database error: {str(exc)}",
        }

    finally:
        db.close()
