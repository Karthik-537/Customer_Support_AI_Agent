# Customer Support AI Agent

A local Customer Support AI Agent for interview-ready Python backend work. This repository currently contains **project structure and configuration only**. Database models, RAG, the agent, tools, memory, and UI logic are not implemented yet.

## Purpose

The planned application will help customers through chat while using company documents, customer memory, and operational tools (orders, inventory, tickets, escalation).

## Planned architecture

```
Customer
   ↓
Streamlit UI
   ↓
FastAPI
   ↓
AI Agent
   ↓
Ollama / Qwen3
   ↓
--------------------------------
| RAG | Memory | Tools |
--------------------------------
   ↓       ↓       ↓
Qdrant  Qdrant   SQLite
                  |
             ----------------
             |      |       |
           Orders Inventory Tickets
```

## Technologies

- Python 3.10+
- FastAPI
- Streamlit
- SQLite + SQLAlchemy
- Qdrant (local, via Docker)
- Ollama with Qwen3:8b
- Sentence Transformers (local embeddings)
- PyMuPDF (PDF processing)

No cloud APIs, LangChain, LangGraph, LlamaIndex, or other agent frameworks.

## Local services required

Before the app can run (once implemented):

1. Python 3.10+ and a virtual environment
2. [Ollama](https://ollama.com/) with the `qwen3:8b` model
3. Docker, for a local Qdrant container

## How to start Ollama

1. Install Ollama from https://ollama.com/
2. Start the Ollama service (it typically listens on `http://localhost:11434`)
3. Pull and run the model:

```bash
ollama pull qwen3:8b
ollama run qwen3:8b
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

The FastAPI app module is a placeholder until the API is implemented.

## How to start Streamlit

```bash
streamlit run streamlit_app.py
```

The Streamlit entrypoint is a placeholder until the UI is implemented.
