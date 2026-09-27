# Customer Support AI Agent

A fully-functional local Customer Support AI Agent demonstrating interview-ready Python backend work. This production-ready system includes complete implementations of database models, RAG, AI agent orchestration, business tools, memory management, and a modern UI.

## Purpose

The application helps customers through chat while using company documents, customer memory, and operational tools (orders, products, tickets). It demonstrates a clean architecture with proper separation of concerns between the frontend, backend API, AI agent, and data layers.

## Architecture

```
Customer
   ↓
Streamlit UI
   ↓
FastAPI Backend
   ↓
AI Agent (Gemini 3.5 Flash Lite)
   ↓
--------------------------------
| RAG | Memory | Tools |
--------------------------------
   ↓       ↓       ↓
Qdrant  Qdrant   SQLite
                  |
             ----------------
             |      |       |
           Orders Products Tickets
```

## Technologies

- Python 3.10+
- FastAPI (REST API backend)
- Streamlit (Customer-facing UI)
- SQLite + SQLAlchemy (Database)
- Qdrant (Vector database, local via Docker)
- Google Gemini 3.5 Flash Lite (LLM)
- Sentence Transformers (Local embeddings - all-MiniLM-L6-v2)
- PyMuPDF (PDF processing)
- JWT Authentication (PyJWT)

No LangChain, LangGraph, LlamaIndex, or other agent frameworks - built from scratch.

## Local services required

Before running the application:

1. Python 3.10+ and a virtual environment
2. A Google Gemini API key
3. Docker, for a local Qdrant container

## Configure Environment
Set these values in `.env`:

```bash
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
API_BASE_URL=http://localhost:8000
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.50
```

## How to run Qdrant

Start Qdrant locally with Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Qdrant should then be available at `http://localhost:6333`.

## How to start FastAPI

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

The FastAPI backend provides REST endpoints for authentication, conversations, and chat.

## How to start Streamlit

```bash
streamlit run streamlit_app.py
```

The Streamlit UI provides a customer-facing chat interface with authentication, conversation management, and real-time AI responses.

## How to ingest knowledge base

```bash
python -m app.rag.ingest
```

This processes PDF documents in the `data/knowledge_base` directory and uploads them to Qdrant for RAG retrieval.

## Features

### Implemented Features

- **Authentication**: JWT-based customer registration and login
- **Conversation Management**: Create, rename, delete, and switch between conversations
- **AI Agent**: Tool-calling agent with Gemini 3.5 Flash Lite
- **Memory System**:
  - Short-term memory (SQLite conversation history)
  - Long-term memory (Qdrant vector storage for user preferences)
- **RAG Integration**: Company policy retrieval from PDF knowledge base
- **Business Tools**:
  - Order status and cancellation checks
  - Product inventory and stock checks
  - Support ticket creation and status queries
- **Customer Isolation**: Strict separation of customer data and conversations
- **Soft Delete**: Safe conversation deletion with recovery potential

### Database Models

- **Customer**: User accounts with email/password authentication
- **Order**: Customer orders with status tracking (PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED)
- **Product**: Inventory with stock levels and pricing
- **SupportTicket**: Customer support requests with priority and status
- **Conversation**: Chat sessions with soft-delete support
- **Message**: Individual message exchanges within conversations

### API Endpoints

- `POST /api/auth/register` - Register new customer
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current customer profile
- `GET /api/customers` - List all customers
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}` - Get conversation details
- `GET /api/conversations/{id}/messages` - Get conversation messages
- `GET /api/users/{user_id}/conversations` - List user conversations
- `PATCH /api/conversations/{id}` - Update conversation
- `DELETE /api/conversations/{id}` - Delete conversation
- `POST /api/chat` - Send message to AI agent

## Project Structure

```
app/
├── agent/              # AI agent orchestration
│   ├── agent.py        # Main agent with tool calling loop
│   ├── llm.py          # Gemini client wrapper
│   ├── prompts.py      # System prompts
│   ├── tool_registry.py # Tool function mapping
│   ├── tool_schemas.py # Tool definitions for LLM
│   ├── memory.py       # Agent memory interface
│   └── rag_interface.py # RAG integration
├── api/                # FastAPI routes
│   ├── routes.py       # API endpoints
│   └── schemas.py      # Pydantic models
├── auth/               # JWT authentication
│   ├── service.py      # Auth logic
│   ├── jwt_utils.py    # JWT token handling
│   └── dependencies.py # Auth dependencies
├── database/           # Database layer
│   ├── db.py           # SQLAlchemy session management
│   └── models.py       # ORM models
├── frontend/           # Streamlit API client
│   └── api_client.py   # HTTP client for backend
├── memory/             # Memory management
│   ├── conversation_memory.py # SQLite conversation storage
│   ├── long_term_memory.py     # Qdrant-based persistent memory
│   ├── context_builder.py      # Context assembly for LLM
│   └── memory_processor.py     # Memory extraction using LLM
├── rag/                # Retrieval Augmented Generation
│   ├── loader.py       # PDF document loading
│   ├── chunker.py      # Document chunking
│   ├── embeddings.py   # Sentence transformer embeddings
│   ├── qdrant_store.py # Qdrant operations
│   ├── retriever.py    # Vector search
│   └── ingest.py       # Knowledge base ingestion script
└── tools/              # Business logic tools
    ├── order_tools.py  # Order status, cancellation
    ├── product_tools.py # Inventory, product search
    └── ticket_tools.py # Support ticket operations
```

## Getting Started

1. **Clone the repository** and navigate to the project directory
2. **Set up environment variables** in `.env` file
3. **Start Qdrant** using Docker
4. **Install dependencies** and activate virtual environment
5. **Run the FastAPI backend** with `uvicorn app.main:app --reload`
6. **Ingest knowledge base** (optional) with `python -m app.rag.ingest`
7. **Start the Streamlit UI** with `streamlit run streamlit_app.py`
8. **Open your browser** to `http://localhost:8501`

## Development

The project follows clean architecture principles with clear separation of concerns:

- **Frontend**: Streamlit UI focuses solely on presentation
- **API Layer**: FastAPI handles authentication, routing, and business logic coordination
- **Agent Layer**: AI agent orchestrates tool calling and reasoning
- **Data Layer**: SQLite and Qdrant handle persistent storage
- **Tools Layer**: Business logic encapsulated in reusable functions

This architecture makes the system maintainable, testable, and extensible.
