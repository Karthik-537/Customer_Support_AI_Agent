"""SQLite engine, session factory, and table initialization."""

from collections.abc import Generator
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Load .env from the project root, not from the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./customer_support.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite allows only one thread per connection by default.
    # FastAPI can use a session from a different thread, so we disable that check.
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)

if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it afterwards.

    FastAPI can later use this as a dependency:
    `db: Session = Depends(get_db)`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_to_use: Engine | None = None) -> None:
    """Create all tables registered on Base.

    Models must be imported first so SQLAlchemy knows about each table.
    """
    from app.database import models  # noqa: F401

    bind = engine_to_use or engine
    Base.metadata.create_all(bind=bind)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DATABASE_URL}")
