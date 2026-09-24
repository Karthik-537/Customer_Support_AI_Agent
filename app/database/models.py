"""SQLAlchemy ORM models for customers, orders, inventory, tickets, and conversations."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class OrderStatus(str, Enum):
    """Allowed values for orders.status."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class TicketPriority(str, Enum):
    """Allowed values for support_tickets.priority."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    """Allowed values for support_tickets.status."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


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
    conversations = relationship("Conversation", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"


class Order(Base):
    """A product order placed by a customer."""

    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orders_quantity_positive"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(SqlEnum(OrderStatus, native_enum=False), nullable=False)
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue = Column(Text, nullable=False)
    priority = Column(SqlEnum(TicketPriority, native_enum=False), nullable=False)
    status = Column(SqlEnum(TicketStatus, native_enum=False), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    customer = relationship("Customer", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<SupportTicket id={self.id} status={self.status!r}>"


class Conversation(Base):
    """A conversation between a user and the AI agent."""

    __tablename__  = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    title = Column(String, nullable=True, default="New Conversation")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0", index=True)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} conversation_id={self.conversation_id!r}>"


class Message(Base):
    """A message within a conversation."""

    __tablename__  = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} conversation_id={self.conversation_id!r}>"
