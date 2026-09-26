"""Support ticket creation and query tools.

This module provides functions to create and query support tickets in SQLite.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session
from enum import Enum

from app.database.db import SessionLocal
from datetime import datetime
from app.database.models import (
    Customer,
    Order,
    SupportTicket,
    TicketPriority,
    TicketStatus,
)

db: Session = SessionLocal()


def _get_matching_customer_orders(
    db: Session,
    customer_id: str,
    product_name: str,
    order_date: Optional[str] = None,
):
    """Find customer orders matching the product name and optionally order date."""

    query = (
        db.query(Order)
        .filter(
            Order.customer_id == customer_id,
            Order.product_name.ilike(f"%{product_name}%"),
        )
    )

    if order_date:
        try:
            order_date = datetime.strptime(order_date, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": "INVALID_DATE_FORMAT",
                "message": "Order date must be in YYYY-MM-DD format.",
            }
        query = query.filter(Order.order_date == order_date)

    return (
        query
        .order_by(Order.order_date.desc())
        .all()
    )


def _build_ticket_payload(
    ticket: SupportTicket,
    product_name: str | None = None,
) -> dict[str, Any]:
    """Build a customer-safe ticket response."""

    payload = {
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
    issue: str,
    product_name: Optional[str] = None,
    priority: str = "MEDIUM",
    order_date: Optional[str] = None
) -> dict[str, Any]:
    """Create a support ticket for a customer's product order."""

    if product_name:
        query = (product_name or "").strip()

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
        if not product_name:
            return _create_general_support_ticket(
                customer_id=customer_id,
                priority=priority_enum,
                issue=issue
            )

        matches = _get_matching_customer_orders(
            db=db,
            customer_id=customer_id,
            product_name=query,
            order_date=order_date
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
                        )
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
            priority=priority_enum.value,
            status=TicketStatus.OPEN.value,
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return {
            "success": True,
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


def _create_general_support_ticket(
    customer_id: str,
    issue: str,
    priority: Enum
) -> dict[str, Any]:
    ticket = SupportTicket(
        customer_id=customer_id,
        order_id=None,
        issue=issue.strip(),
        priority=priority.value,
        status=TicketStatus.OPEN.value,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
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
