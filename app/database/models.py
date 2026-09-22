"""SQLAlchemy ORM models for customers, orders, inventory, and tickets."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


def utc_now() -> datetime:
    """Return the current UTC time for default timestamps."""
    return datetime.now(timezone.utc)


class Customer(Base):
    """A customer who can place orders and open support tickets."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    orders = relationship("Order", back_populates="customer")
    tickets = relationship("SupportTicket", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"


class Order(Base):
    """A product order placed by a customer."""

    __tablename__ = "orders"

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_SHIPPED = "SHIPPED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CANCELLED = "CANCELLED"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orders_quantity_positive"),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED')",
            name="ck_orders_status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    order_date = Column(DateTime, nullable=False, default=utc_now)
    delivery_date = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status!r}>"


class Inventory(Base):
    """A product that can be sold, including current stock and price."""

    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_inventory_stock_non_negative"),
        CheckConstraint("price >= 0", name="ck_inventory_price_non_negative"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, nullable=False, unique=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        return f"<Inventory product_id={self.product_id!r} stock={self.stock_quantity}>"


class SupportTicket(Base):
    """A support request opened by a customer."""

    __tablename__ = "support_tickets"

    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_CRITICAL = "CRITICAL"

    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_ESCALATED = "ESCALATED"
    STATUS_CLOSED = "CLOSED"

    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED', 'CLOSED')",
            name="ck_tickets_status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue = Column(Text, nullable=False)
    priority = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    customer = relationship("Customer", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<SupportTicket id={self.id} status={self.status!r}>"
