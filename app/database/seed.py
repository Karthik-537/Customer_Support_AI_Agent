"""Insert fictional demo data into the SQLite database."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.db import SessionLocal, init_db
from app.database.models import Customer, Inventory, Order, SupportTicket


def _utc(days_ago: int = 0, hour: int = 12) -> datetime:
    now = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0)
    return now - timedelta(days=days_ago)


def clear_tables(db: Session) -> None:
    """Remove existing rows so the seed script can be re-run safely."""
    db.query(SupportTicket).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.query(Inventory).delete()
    db.commit()


def seed_inventory(db: Session) -> list[Inventory]:
    products = [
        Inventory(
            product_id="NB-1001",
            product_name="NovaBook 14 Laptop",
            category="Laptops",
            stock_quantity=18,
            price=899.00,
        ),
        Inventory(
            product_id="NB-2001",
            product_name="NovaBook Pro 16",
            category="Laptops",
            stock_quantity=7,
            price=1499.00,
        ),
        Inventory(
            product_id="HP-3001",
            product_name="Pulse Wireless Headphones",
            category="Audio",
            stock_quantity=42,
            price=129.99,
        ),
        Inventory(
            product_id="HP-3002",
            product_name="Pulse Noise-Canceling Headphones",
            category="Audio",
            stock_quantity=1,
            price=249.00,
        ),
        Inventory(
            product_id="KB-4001",
            product_name="Clickety Mechanical Keyboard",
            category="Accessories",
            stock_quantity=25,
            price=89.50,
        ),
        Inventory(
            product_id="MS-5001",
            product_name="Orbit Wireless Mouse",
            category="Accessories",
            stock_quantity=0,
            price=39.99,
        ),
        Inventory(
            product_id="MN-6001",
            product_name="Vista 27-inch Monitor",
            category="Monitors",
            stock_quantity=12,
            price=279.00,
        ),
        Inventory(
            product_id="CH-7001",
            product_name="RapidCharge USB-C Hub",
            category="Accessories",
            stock_quantity=33,
            price=54.00,
        ),
        Inventory(
            product_id="CB-8001",
            product_name="Aero Smartwatch",
            category="Wearables",
            stock_quantity=0,
            price=199.00,
        ),
        Inventory(
            product_id="SP-9001",
            product_name="Echo Portable Speaker",
            category="Audio",
            stock_quantity=15,
            price=79.00,
        ),
    ]
    db.add_all(products)
    db.flush()
    return products


def seed_customers(db: Session) -> list[Customer]:
    customers = [
        Customer(name="Ava Patel", email="ava.patel@example.com", created_at=_utc(40)),
        Customer(name="Liam Chen", email="liam.chen@example.com", created_at=_utc(35)),
        Customer(name="Sofia Rossi", email="sofia.rossi@example.com", created_at=_utc(28)),
        Customer(name="Noah Williams", email="noah.williams@example.com", created_at=_utc(20)),
        Customer(name="Maya Johnson", email="maya.johnson@example.com", created_at=_utc(12)),
    ]
    db.add_all(customers)
    db.flush()
    return customers


def seed_orders(db: Session, customers: list[Customer]) -> list[Order]:
    ava, liam, sofia, noah, maya = customers
    orders = [
        Order(
            customer_id=ava.id,
            product_id="NB-1001",
            product_name="NovaBook 14 Laptop",
            quantity=1,
            status=Order.STATUS_DELIVERED,
            order_date=_utc(30),
            delivery_date=_utc(25),
        ),
        Order(
            customer_id=ava.id,
            product_id="HP-3001",
            product_name="Pulse Wireless Headphones",
            quantity=2,
            status=Order.STATUS_SHIPPED,
            order_date=_utc(5),
        ),
        Order(
            customer_id=liam.id,
            product_id="NB-2001",
            product_name="NovaBook Pro 16",
            quantity=1,
            status=Order.STATUS_CONFIRMED,
            order_date=_utc(2),
        ),
        Order(
            customer_id=liam.id,
            product_id="KB-4001",
            product_name="Clickety Mechanical Keyboard",
            quantity=1,
            status=Order.STATUS_PENDING,
            order_date=_utc(0, hour=9),
        ),
        Order(
            customer_id=sofia.id,
            product_id="MN-6001",
            product_name="Vista 27-inch Monitor",
            quantity=2,
            status=Order.STATUS_SHIPPED,
            order_date=_utc(8),
        ),
        Order(
            customer_id=sofia.id,
            product_id="MS-5001",
            product_name="Orbit Wireless Mouse",
            quantity=1,
            status=Order.STATUS_CANCELLED,
            order_date=_utc(10),
        ),
        Order(
            customer_id=noah.id,
            product_id="CH-7001",
            product_name="RapidCharge USB-C Hub",
            quantity=3,
            status=Order.STATUS_DELIVERED,
            order_date=_utc(18),
            delivery_date=_utc(14),
        ),
        Order(
            customer_id=noah.id,
            product_id="HP-3002",
            product_name="Pulse Noise-Canceling Headphones",
            quantity=1,
            status=Order.STATUS_PENDING,
            order_date=_utc(1),
        ),
        Order(
            customer_id=maya.id,
            product_id="SP-9001",
            product_name="Echo Portable Speaker",
            quantity=1,
            status=Order.STATUS_CONFIRMED,
            order_date=_utc(3),
        ),
        Order(
            customer_id=maya.id,
            product_id="CB-8001",
            product_name="Aero Smartwatch",
            quantity=1,
            status=Order.STATUS_CANCELLED,
            order_date=_utc(7),
        ),
    ]
    db.add_all(orders)
    db.flush()
    return orders


def seed_tickets(db: Session, customers: list[Customer]) -> list[SupportTicket]:
    ava, liam, sofia, noah, maya = customers
    tickets = [
        SupportTicket(
            customer_id=ava.id,
            issue="Laptop charger from order NB-1001 stopped working after two weeks.",
            priority=SupportTicket.PRIORITY_HIGH,
            status=SupportTicket.STATUS_OPEN,
            created_at=_utc(4),
        ),
        SupportTicket(
            customer_id=liam.id,
            issue="Need to change the shipping address for my NovaBook Pro 16 order.",
            priority=SupportTicket.PRIORITY_MEDIUM,
            status=SupportTicket.STATUS_IN_PROGRESS,
            created_at=_utc(1),
        ),
        SupportTicket(
            customer_id=sofia.id,
            issue="Monitor arrived with a dead pixel. Requesting a replacement.",
            priority=SupportTicket.PRIORITY_HIGH,
            status=SupportTicket.STATUS_ESCALATED,
            created_at=_utc(6),
        ),
        SupportTicket(
            customer_id=noah.id,
            issue="USB-C hub was missing from the package. Replacement already received.",
            priority=SupportTicket.PRIORITY_LOW,
            status=SupportTicket.STATUS_RESOLVED,
            created_at=_utc(16),
        ),
        SupportTicket(
            customer_id=maya.id,
            issue="Cancelled Aero Smartwatch order but the charge is still on my card.",
            priority=SupportTicket.PRIORITY_CRITICAL,
            status=SupportTicket.STATUS_OPEN,
            created_at=_utc(2),
        ),
    ]
    db.add_all(tickets)
    db.flush()
    return tickets


def seed() -> dict[str, int]:
    """Create tables if needed, replace demo rows, and return counts."""
    init_db()
    db = SessionLocal()
    try:
        clear_tables(db)
        customers = seed_customers(db)
        products = seed_inventory(db)
        orders = seed_orders(db, customers)
        tickets = seed_tickets(db, customers)
        db.commit()
        return {
            "customers": len(customers),
            "orders": len(orders),
            "inventory": len(products),
            "support_tickets": len(tickets),
        }
    finally:
        db.close()


if __name__ == "__main__":
    counts = seed()
    print("Seed complete:")
    for table_name, count in counts.items():
        print(f"  {table_name}: {count}")
