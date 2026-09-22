"""Order status and cancellation tools.

This module provides functions to query and update order records in SQLite.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Order, OrderStatus


def get_order_status(order_id: int) -> dict[str, Any]:
    """Retrieve order information by order ID.

    Args:
        order_id: The ID of the order to retrieve.

    Returns:
        A dictionary containing order information if found:
        {
            "success": true,
            "order_id": int,
            "customer_id": int,
            "product_id": str,
            "product_name": str,
            "quantity": int,
            "status": str,
            "order_date": str,
            "delivery_date": str | None
        }

        If the order does not exist:
        {
            "success": false,
            "error": "Order not found"
        }
    """
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
            "status": order.status.value,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()


def cancel_order(order_id: int) -> dict[str, Any]:
    """Cancel an order if it is in a cancellable state.

    An order can only be cancelled if its current status is PENDING or CONFIRMED.
    Orders that are SHIPPED, DELIVERED, or already CANCELLED cannot be cancelled.

    Args:
        order_id: The ID of the order to cancel.

    Returns:
        If cancellation succeeds:
        {
            "success": true,
            "order_id": int,
            "status": "CANCELLED",
            "message": "Order cancelled successfully"
        }

        If cancellation is not allowed:
        {
            "success": false,
            "order_id": int,
            "status": str,
            "error": str
        }

        If the order doesn't exist:
        {
            "success": false,
            "error": "Order not found"
        }
    """
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            return {"success": False, "error": "Order not found"}

        if order.status == OrderStatus.CANCELLED:
            return {
                "success": False,
                "order_id": order.id,
                "status": order.status.value,
                "error": "Order cannot be cancelled because it is already cancelled.",
            }

        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            return {
                "success": False,
                "order_id": order.id,
                "status": order.status.value,
                "error": f"Order cannot be cancelled because it has already been {order.status.value.lower()}.",
            }

        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            return {
                "success": False,
                "order_id": order.id,
                "status": order.status.value,
                "error": f"Order cannot be cancelled in its current state: {order.status.value}.",
            }

        order.status = OrderStatus.CANCELLED
        db.commit()

        return {
            "success": True,
            "order_id": order.id,
            "status": order.status.value,
            "message": "Order cancelled successfully",
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()
