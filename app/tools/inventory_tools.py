"""Inventory and stock-checking tools.

This module provides functions to query inventory records in SQLite.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Inventory


def check_inventory(product_id: str) -> dict[str, Any]:
    """Check whether a product is currently available.

    This is a READ operation only and does not modify inventory.

    Args:
        product_id: The ID of the product to check.

    Returns:
        If the product exists:
        {
            "success": true,
            "product_id": str,
            "product_name": str,
            "category": str,
            "stock_quantity": int,
            "price": float,
            "in_stock": bool
        }

        If the product does not exist:
        {
            "success": false,
            "error": "Product not found"
        }
    """
    db: Session = SessionLocal()
    try:
        product = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        if product is None:
            return {"success": False, "error": "Product not found"}

        return {
            "success": True,
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category": product.category,
            "stock_quantity": product.stock_quantity,
            "price": product.price,
            "in_stock": product.stock_quantity > 0,
        }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        db.close()
