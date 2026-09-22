"""Tests for the SQLite / SQLAlchemy database layer."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database.db import Base, init_db
from app.database.models import Customer, Inventory, Order, SupportTicket


def _enable_foreign_keys(engine) -> None:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture
def db_session() -> Session:
    """Isolated in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _enable_foreign_keys(engine)
    init_db(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_database_initialization(tmp_path: Path) -> None:
    db_file = tmp_path / "customer_support.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    init_db(engine)

    assert db_file.exists()
    table_names = set(inspect(engine).get_table_names())
    assert table_names == {"customers", "orders", "inventory", "support_tickets"}


def test_customer_creation(db_session: Session) -> None:
    customer = Customer(name="Ava Patel", email="ava.patel@example.com")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    assert customer.id is not None
    assert customer.name == "Ava Patel"
    assert customer.email == "ava.patel@example.com"
    assert customer.created_at is not None


def test_order_creation(db_session: Session) -> None:
    customer = Customer(name="Liam Chen", email="liam.chen@example.com")
    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        product_id="NB-1001",
        product_name="NovaBook 14 Laptop",
        quantity=1,
        status=Order.STATUS_PENDING,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    assert order.id is not None
    assert order.customer_id == customer.id
    assert order.quantity == 1
    assert order.status == "PENDING"
    assert order.delivery_date is None


def test_customer_orders_relationship(db_session: Session) -> None:
    customer = Customer(name="Sofia Rossi", email="sofia.rossi@example.com")
    db_session.add(customer)
    db_session.flush()

    first = Order(
        customer_id=customer.id,
        product_id="HP-3001",
        product_name="Pulse Wireless Headphones",
        quantity=2,
        status=Order.STATUS_CONFIRMED,
    )
    second = Order(
        customer_id=customer.id,
        product_id="KB-4001",
        product_name="Clickety Mechanical Keyboard",
        quantity=1,
        status=Order.STATUS_SHIPPED,
    )
    db_session.add_all([first, second])
    db_session.commit()
    db_session.refresh(customer)

    assert len(customer.orders) == 2
    assert {order.product_id for order in customer.orders} == {"HP-3001", "KB-4001"}
    assert first.customer.email == "sofia.rossi@example.com"


def test_inventory_creation(db_session: Session) -> None:
    item = Inventory(
        product_id="MS-5001",
        product_name="Orbit Wireless Mouse",
        category="Accessories",
        stock_quantity=0,
        price=39.99,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.product_id == "MS-5001"
    assert item.stock_quantity == 0
    assert item.price == 39.99
    assert item.created_at is not None
    assert item.updated_at is not None


def test_inventory_product_id_uniqueness(db_session: Session) -> None:
    db_session.add(
        Inventory(
            product_id="NB-1001",
            product_name="NovaBook 14 Laptop",
            category="Laptops",
            stock_quantity=10,
            price=899.00,
        )
    )
    db_session.commit()

    db_session.add(
        Inventory(
            product_id="NB-1001",
            product_name="Duplicate NovaBook",
            category="Laptops",
            stock_quantity=1,
            price=850.00,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_support_ticket_creation(db_session: Session) -> None:
    customer = Customer(name="Noah Williams", email="noah.williams@example.com")
    db_session.add(customer)
    db_session.flush()

    ticket = SupportTicket(
        customer_id=customer.id,
        issue="USB-C hub was missing from the package.",
        priority=SupportTicket.PRIORITY_MEDIUM,
        status=SupportTicket.STATUS_OPEN,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    assert ticket.id is not None
    assert ticket.customer_id == customer.id
    assert "USB-C hub" in ticket.issue
    assert ticket.priority == "MEDIUM"
    assert ticket.status == "OPEN"


def test_customer_support_tickets_relationship(db_session: Session) -> None:
    customer = Customer(name="Maya Johnson", email="maya.johnson@example.com")
    db_session.add(customer)
    db_session.flush()

    open_ticket = SupportTicket(
        customer_id=customer.id,
        issue="Refund still pending after cancellation.",
        priority=SupportTicket.PRIORITY_CRITICAL,
        status=SupportTicket.STATUS_OPEN,
    )
    resolved_ticket = SupportTicket(
        customer_id=customer.id,
        issue="Asked for an invoice copy. Sent by email.",
        priority=SupportTicket.PRIORITY_LOW,
        status=SupportTicket.STATUS_RESOLVED,
    )
    db_session.add_all([open_ticket, resolved_ticket])
    db_session.commit()
    db_session.refresh(customer)

    assert len(customer.tickets) == 2
    assert {ticket.status for ticket in customer.tickets} == {"OPEN", "RESOLVED"}
    assert open_ticket.customer.name == "Maya Johnson"
