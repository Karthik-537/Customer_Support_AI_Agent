"""Human escalation tools.

This module provides functions to escalate customer issues to human support.
"""

from typing import Any

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


def _matching_customer_orders(
    db: Session,
    customer_id: str,
    product_name: str,
) -> list[Order]:
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


def escalate_to_human(
    customer_id: str,
    product_name: str,
    reason: str,
) -> dict[str, Any]:
    """Escalate a customer issue to human support for a matched product order."""

    query = (product_name or "").strip()

    if not query:
        return {
            "success": False,
            "error": "Product name is required",
        }

    if not reason or not reason.strip():
        return {
            "success": False,
            "error": "Reason is required",
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

        matches = _matching_customer_orders(
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
                    "before escalating."
                ),
            }

        selected_order = matches[0]

        ticket = SupportTicket(
            customer_id=customer_id,
            order_id=selected_order.id,
            issue=reason.strip(),
            priority=TicketPriority.HIGH,
            status=TicketStatus.ESCALATED,
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "success": True,
            "ticket_reference": _build_ticket_reference(ticket.id),
            "product_name": selected_order.product_name,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "message": "Issue escalated to human support.",
        }

    except Exception as exc:
        db.rollback()

        return {
            "success": False,
            "error": f"Database error: {str(exc)}",
        }

    finally:
        db.close()