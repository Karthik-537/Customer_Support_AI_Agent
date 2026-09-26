"""Inventory and stock-checking tools.

This module provides functions to query inventory records in SQLite.
Customer-facing responses are intentionally sanitized and do not expose internal IDs.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import Product


def _sanitize_inventory(product: Product) -> dict[str, Any]:
    """Return a customer-safe inventory summary without internal IDs."""
    return {
        "product_name": product.product_name,
        "category": product.category,
        "stock_quantity": product.stock_quantity,
        "price": product.price,
    }


def check_product(product_id: str) -> dict[str, Any]:
    """Internal exact lookup for inventory by product identifier."""
    db: Session = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product is None:
            return {"success": False, "error": "Product not found"}

        return {
            "success": True,
            "product_id": product.id,
            "product_name": product.product_name,
            "category": product.category,
            "stock_quantity": product.stock_quantity,
            "price": product.price,
            "in_stock": product.stock_quantity > 0,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def check_product_by_name(product_name: str) -> dict[str, Any]:
    """Return all matching products for a customer-friendly product-name search."""
    query = (product_name or "").strip()
    if not query:
        return {"success": False, "error": "Product name is required"}

    db: Session = SessionLocal()
    try:
        matches = (
            db.query(Product)
            .filter(Product.product_name.ilike(f"%{query}%"))
            .order_by(Product.product_name.asc())
            .all()
        )
        return {
            "success": True,
            "count": len(matches),
            "items": [_sanitize_inventory(product=item) for item in matches],
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"success": False, "error": f"Database error: {str(exc)}"}
    finally:
        db.close()
