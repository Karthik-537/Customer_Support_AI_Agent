"""SQLite engine, session factory, and table initialization."""

from collections.abc import Generator
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
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
    _migrate_legacy_message_schema(bind)


def _migrate_legacy_message_schema(bind: Engine) -> None:
    """Upgrade legacy message and conversation deletion schemas."""
    inspector = inspect(bind)
    conversation_columns = {column["name"] for column in inspector.get_columns("conversations")}
    message_columns = {column["name"] for column in inspector.get_columns("messages")}

    with bind.begin() as connection:
        if "is_deleted" not in conversation_columns:
            connection.execute(
                text("ALTER TABLE conversations ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0")
            )
        if "deleted_at" in conversation_columns:
            connection.execute(
                text(
                    "UPDATE conversations SET is_deleted = "
                    "CASE WHEN deleted_at IS NOT NULL THEN 1 ELSE 0 END"
                )
            )

        if {"role", "content"}.issubset(message_columns):
            legacy_rows = connection.execute(text(
                "SELECT conversation_id, role, content, created_at "
                "FROM messages ORDER BY conversation_id, id"
            )).mappings().all()

            exchanges = []
            pending_users = {}
            for row in legacy_rows:
                conversation_id = row["conversation_id"]
                if row["role"] == "user":
                    if conversation_id in pending_users:
                        previous = pending_users.pop(conversation_id)
                        exchanges.append(previous)
                    pending_users[conversation_id] = {
                        "conversation_id": conversation_id,
                        "user_message": row["content"],
                        "response": "",
                        "created_at": row["created_at"],
                    }
                elif row["role"] == "assistant":
                    pending = pending_users.pop(conversation_id, None)
                    if pending:
                        pending["response"] = row["content"]
                        exchanges.append(pending)
                    else:
                        exchanges.append({
                            "conversation_id": conversation_id,
                            "user_message": "",
                            "response": row["content"],
                            "created_at": row["created_at"],
                        })

            exchanges.extend(pending_users.values())
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text("DROP TABLE messages"))
            connection.execute(text(
                "CREATE TABLE messages ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "conversation_id VARCHAR NOT NULL, "
                "user_message TEXT NOT NULL, "
                "response TEXT NOT NULL, "
                "created_at DATETIME NOT NULL, "
                "FOREIGN KEY(conversation_id) REFERENCES conversations (conversation_id)"
                ")"
            ))
            connection.execute(text("CREATE INDEX ix_messages_conversation_id ON messages (conversation_id)"))
            if exchanges:
                connection.execute(
                    text(
                        "INSERT INTO messages "
                        "(conversation_id, user_message, response, created_at) "
                        "VALUES (:conversation_id, :user_message, :response, :created_at)"
                    ),
                    exchanges,
                )
            connection.execute(text("PRAGMA foreign_keys=ON"))


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DATABASE_URL}")
