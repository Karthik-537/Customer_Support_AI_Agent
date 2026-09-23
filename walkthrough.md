# Customer Support AI Agent — Phase 9 Streamlit Walkthrough

This document summarizes the current Streamlit-based customer support UI, how it fits into the existing architecture, and the main issues to review in the surrounding backend code.

## Overview

The project is designed as a local customer-support AI system with a clear separation of responsibilities:

- Streamlit handles presentation and user interaction
- The existing backend agent handles orchestration and tool calling
- SQLite stores customer, order, ticket, and conversation data
- Qdrant stores vector memory and knowledge-base retrieval data
- Ollama + Qwen3 provides the LLM reasoning layer

The intended architecture remains:

```text
Streamlit
    ↓
Agent
    ↓
Qwen3
 ├── Memory
 ├── RAG
 └── Tools
      ↓
SQLite / Qdrant
```

This keeps the UI thin and avoids mixing business logic into the frontend.

---

## What the Streamlit UI is responsible for

`streamlit_app.py` is the customer-facing interface. It is responsible for:

- selecting a customer from the local demo database
- creating a new conversation
- switching between conversations
- displaying conversation history
- sending user messages to the existing backend agent
- showing the AI response
- refreshing state from the database
- renaming conversation titles

It does not implement the logic for:

- LLM orchestration
- tool calling
- knowledge retrieval
- long-term memory
- inventory logic
- DB write operations beyond using the existing services

---

## Sample UI layout

### Sidebar

```text
┌──────────────────────────────────────────────────────┐
│ Customer Support AI                                  │
├──────────────────────────────────────────────────────┤
│ Customer                                             │
│ [Alice Johnson (alice@example.com) ▼]                │
│                                                      │
│ [ + New Conversation ]                               │
│                                                      │
│ Conversations                                        │
│ • Order cancellation                                  │
│ • Warranty question                                   │
│ • Damaged laptop                                      │
│ • Previous issue                                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Main chat area

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Customer Support AI                                                     │
├────────────────────────────────────────────────────────────────────────────┤
│ Customer: Alice Johnson                          │ Rename │             │
│ Conversation ID: 7f2a9...                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ User: My order hasn't arrived yet.                                     │
│ AI: I can help check that. Let me look up the current order status.    │
│                                                                        │
│ User: Can I cancel it?                                                 │
│ AI: I’m checking your order and the cancellation policy.               │
│                                                                        │
│ User: My laptop arrived damaged.                                       │
│ AI: I’m sorry to hear that. I can help with your warranty or return    │
│    options.                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ [ Type your message... ]                                               │
└────────────────────────────────────────────────────────────────────────────┘
```

### Empty state

```text
┌──────────────────────────────────────────────────────┐
│ Customer Support AI                                  │
├──────────────────────────────────────────────────────┤
│ Welcome to Customer Support, Alice!                  │
│                                                     │
│ I can help with:                                     │
│ - Orders                                            │
│ - Shipping                                          │
│ - Refunds                                           │
│ - Warranty                                          │
│ - Stock checks                                      │
│ - Support tickets                                    │
│                                                     │
│ Select a conversation or start a new one.            │
│                                                     │
│ [ Type your message... ]                             │
└──────────────────────────────────────────────────────┘
```

---

## Current runtime flow

The flow implemented by the app is:

```text
Customer selected
        ↓
Load that customer's conversations
        ↓
Open or create a conversation
        ↓
Load conversation history from SQLite
        ↓
User enters message via st.chat_input()
        ↓
Call existing backend agent.process_message(...)
        ↓
Display AI response in chat
        ↓
Refresh from the backend/database
```

This matches the desired architecture where Streamlit remains the UI layer and the backend remains the decision and data layer.

---

## Existing backend APIs already in use

The UI uses the existing backend services rather than creating new logic. The relevant APIs/functions include:

- conversation creation
  - `create_conversation(...)`
  - `get_or_create_conversation(...)`

- conversation retrieval
  - `get_conversation(...)`
  - `list_user_conversations(...)`

- message retrieval
  - `get_messages(...)`
  - `get_recent_messages(...)`

- conversation updates
  - `update_conversation(...)`

- message writes
  - `add_message(...)`

- agent runtime
  - `CustomerSupportAgent.process_message(...)`
  - `get_agent()` / `get_support_agent()`

This is exactly how the app should remain structured: the UI connects to the existing services, not a separate implementation.

---

## Customer isolation design

The code is designed to enforce customer separation:

- the sidebar only loads customers from SQLite
- conversations are loaded only for the selected customer
- the UI checks conversation ownership before displaying the active conversation
- switching customers clears the active conversation if it belongs to another customer

This is important because the user-facing UI must not act as the only security boundary. The backend ownership validation remains the actual enforcement point.

---

## Conversation ID handling

The app correctly follows the Phase 7 model:

- a conversation is created in the backend
- a persistent `conversation_id` is generated
- the UI stores only the active one in `st.session_state`
- messages are sent to the backend using that `conversation_id`
- SQLite remains the source of truth for the full conversation record

This is the correct architecture and should be kept unchanged.

---

## Phase 9 strengths already present

The current implementation already includes the expected UI features:

- customer selector
- “New Conversation” button
- list of past conversations
- active conversation selection
- chat history rendering
- renaming a conversation
- customer switching logic
- database-backed persistence
- backend agent invocation through the existing service

This is a strong Phase 9 result and matches the project’s intended design.

---

## Issues to review and recommended fixes

### 1) `delete_conversation()` session variable handling

In `app/memory/conversation_memory.py`, the delete flow should assign the session result to a variable before using it.

Current pattern:

```python
# existing code

db = SessionLocal()
try:
    db.query(Conversation)...
```

Recommended pattern:

```python
db: Session = SessionLocal()
try:
    db.query(Conversation)...
    db.commit()
finally:
    db.close()
```

Why this matters:
- keeps the code consistent with the rest of the module
- prevents subtle runtime issues during cleanup
- ensures reliable deletion behavior

---

### 2) Incorrect package import in `memory_processor.py`

The project currently uses a fragile import pattern:

```python
from long_term_memory import MEMORY_COLLECTION
```

This should be:

```python
from app.memory.long_term_memory import MEMORY_COLLECTION
```

Why this matters:
- avoids import errors when running from different working directories
- matches the project package structure
- keeps module execution predictable

---

### 3) Memory extraction may not match the actual Ollama response model

In `app/memory/memory_extractor.py`, the code checks for a `success` field:

```python
if not response.get("success"):
```

But the raw Ollama response often looks more like a chat payload with `message` content rather than a custom `success` flag.

Safer handling is:

```python
content = response.get("message", {}).get("content", "")
if not content:
    logger.warning("Memory extraction returned no content")
    return []
```

Why this matters:
- prevents false negatives during memory extraction
- makes the code match the actual Ollama response shape

---

### 4) Duplicate memory context in `context_builder.py`

The memory context is currently appended in more than one place. This can create repeated prompt content and noisy LLM context.

Recommended fix:
- build the memory context once
- append it only once to the system message list

Why this matters:
- cleaner prompt construction
- better clarity for the model
- reduced chance of redundant context

---

### 5) Runtime dependency handling should remain calm and customer-friendly

If Ollama or Qdrant is unavailable, the UI should continue to show a graceful customer-facing error without exposing internals.

Recommended pattern:

```python
st.error("Sorry, I couldn't process your request right now. Please try again.")
```

Why this matters:
- better UX
- keeps technical logs separate from customer-visible output
- avoids exposing stack traces in the app

---

## Recommended next steps

The next improvements should stay focused and minimal:

1. fix the session handling bug in `conversation_memory.py`
2. correct the import in `memory_processor.py`
3. align memory extraction with the actual Ollama API response format
4. remove duplicate memory context injection in `context_builder.py`
5. keep Streamlit as a presentation layer only

These changes are not architecture changes; they are correctness and reliability improvements.

---

## Final assessment

The project already reflects a good Phase 9 implementation:

- the UI is thin and presentation-focused
- the backend remains responsible for the agent, memory, RAG, and tools
- SQLite and Qdrant remain the persistence layers
- `conversation_id` handling follows the intended pattern
- customer conversation isolation is implemented correctly

The main follow-up work is in the underlying backend correctness, not in the UI design itself.