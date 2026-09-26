"""Order status and cancellation tools.

This module provides functions to query and update order records in SQLite.
Customer-facing responses are intentionally sanitized and do not expose internal IDs.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Order, OrderStatus


def _sanitize_order(order: Order) -> dict[str, Any]:
    """Return a customer-safe order summary without internal identifiers."""
    return {
        "product_name": order.product_name,
        "quantity": order.quantity,
        "status": order.status.value if isinstance(order.status, OrderStatus) else str(order.status),
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
    }


def get_order_details(order_id: str) -> dict[str, Any]:
    """Internal exact lookup used by backend logic and tool orchestration."""
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            return {"success": False, "error": "Order not found"}
        return {
            "success": True,
            "order_id": order.id,
            "customer_id": order.customer_id,
            "product_id": order.product_id,
            "product_name": order.product_name,
            "quantity": order.quantity,
            "status": order.status.value if isinstance(order.status, OrderStatus) else str(order.status),
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_my_orders(customer_id: str) -> dict[str, Any]:
    """Return all orders for a given customer in customer-safe format."""
    db: Session = SessionLocal()
    try:
        orders = (
            db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_date.desc())
            .all()
        )
        return {
            "success": True,
            "count": len(orders),
            "orders": [_sanitize_order(order) for order in orders],
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_orders_by_product_name(customer_id: str, product_name: str) -> dict[str, Any]:
    """Return all matching customer orders for a product name search."""
    query = (product_name or "").strip()
    if not query:
        return {"success": False, "error": "Product name is required"}

    db: Session = SessionLocal()
    try:
        matches = (
            db.query(Order)
            .filter(
                Order.customer_id == customer_id,
                Order.product_name.ilike(f"%{query}%"),
            )
            .order_by(Order.order_date.desc())
            .all()
        )
        return {
            "success": True,
            "count": len(matches),
            "matches": [_sanitize_order(order) for order in matches],
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_order_status(order_id: str) -> dict[str, Any]:
    """Internal exact status lookup for tool orchestration."""
    return get_order_details(order_id)


def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel an order if it is in a cancellable state."""
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            return {"success": False, "error": "Order not found"}

        current_status = order.status.value if isinstance(order.status, OrderStatus) else str(order.status)

        if current_status == OrderStatus.CANCELLED.value:
            return {"success": False, "order_id": order.id, "status": current_status, "error": "Order cannot be cancelled because it is already cancelled."}

        if current_status in [OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value]:
            return {"success": False, "order_id": order.id, "status": current_status, "error": f"Order cannot be cancelled because it has already been {current_status.lower()}."}

        if current_status not in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]:
            return {"success": False, "order_id": order.id, "status": current_status, "error": f"Order cannot be cancelled in its current state: {current_status}."}

        order.status = OrderStatus.CANCELLED.value
        db.commit()

        return {
            "success": True,
            "order_id": order.id,
            "status": order.status.value if isinstance(order.status, OrderStatus) else str(order.status),
            "message": "Order cancelled successfully",
        }
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()
