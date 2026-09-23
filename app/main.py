"""FastAPI application entrypoint for the Customer Support AI Agent."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database.db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Customer Support AI Agent API",
    description="Local customer support backend with agent, RAG, memory, and tool orchestration.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize the SQLite database when the API starts."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.exception("Failed to initialize database on startup")
        raise exc


app.include_router(router)
