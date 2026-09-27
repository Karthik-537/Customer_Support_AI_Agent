# Customer Support AI Agent — Implementation Walkthrough

This document summarizes the current customer support system implementation, architecture, and usage.

## Overview

The project is a fully-implemented local customer-support AI system with a clear separation of responsibilities:

- Streamlit handles presentation and user interaction
- FastAPI backend provides REST API endpoints
- The AI agent handles orchestration and tool calling
- SQLite stores customer, order, ticket, and conversation data
- Qdrant stores vector memory and knowledge-base retrieval data
- Google Gemini 3.5 Flash Lite provides the LLM reasoning layer

The architecture:

```text
Streamlit UI
    ↓
FastAPI Backend
    ↓
AI Agent (Gemini)
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

- User authentication (login/register with JWT)
- Creating a new conversation
- Switching between conversations
- Displaying conversation history
- Sending user messages to the backend API
- Showing the AI response
- Refreshing state from the backend
- Renaming and deleting conversation titles
- Customer session management

It does not implement the logic for:

- LLM orchestration
- tool calling
- knowledge retrieval
- long-term memory
- inventory logic
- DB write operations (delegated to FastAPI backend)

---

## Sample UI layout

### Sidebar

```text
┌──────────────────────────────────────────────────────┐
│ Customer Support AI                                  │
├──────────────────────────────────────────────────────┤
│ Logged in as: Alice Johnson                          │
│ (alice@example.com)                                  │
│                                                      │
│ [Logout]                                             │
│                                                      │
│ [ ➕ New Conversation ]                              │
│                                                      │
│ Conversations                                        │
│ • Order cancellation                                 │
│ • Warranty question                                  │
│ • Damaged laptop                                     │
│ • Previous issue                                     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Main chat area

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 💬 Order cancellation                                        ⋯           │
│ Customer: Alice Johnson                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│ User: My order hasn't arrived yet.                                     │
│ AI: I can help check that. Let me look up the current order status.    │
│                                                                        │
│ User: Can I cancel it?                                                 │
│ AI: I'm checking your order and the cancellation policy.               │
│                                                                        │
│ User: My laptop arrived damaged.                                       │
│ AI: I'm sorry to hear that. I can help with your warranty or return    │
│    options.                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ [ How can we help you today? ]                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

### Empty state

```text
┌──────────────────────────────────────────────────────┐
│ Customer Support AI                                  │
├──────────────────────────────────────────────────────┤
│ Welcome to Customer Support, Alice!                  │
│                                                     │
│ I am your local AI support assistant. I can help you │
│ with:                                               │
│                                                     │
│ - 📦 Order Status                                   │
│ - 🚫 Order Cancellations                            │
│ - 📋 Company Policies                               │
│ - 🔍 Product & Stock                                │
│ - 🎫 Support Tickets                                │
│                                                     │
│ 👉 To get started, select a past conversation from  │
│ the sidebar, click ➕ New Conversation, or simply    │
│ type your message below.                             │
│                                                     │
│ [ How can we help you today? ]                       │
└──────────────────────────────────────────────────────┘
```

---

## Current runtime flow

The flow implemented by the app is:

```text
User logs in via JWT authentication
        ↓
Load user's conversations from backend API
        ↓
Open or create a conversation
        ↓
Load conversation history from SQLite via API
        ↓
User enters message via st.chat_input()
        ↓
Send message to FastAPI backend
        ↓
Backend calls agent.process_message(...)
        ↓
Agent uses tools, memory, and RAG
        ↓
Display AI response in chat
        ↓
Refresh from the backend API
```

This matches the desired architecture where Streamlit remains the UI layer, FastAPI handles API logic, and the agent handles decision-making.

---

## Existing backend APIs already in use

The UI uses the FastAPI backend via HTTP client. The relevant API endpoints include:

- Authentication
  - `POST /api/auth/register` - Register new customer
  - `POST /api/auth/login` - Login and get JWT token
  - `GET /api/auth/me` - Get current customer profile

- Conversation management
  - `POST /api/conversations` - Create new conversation
  - `GET /api/conversations/{id}` - Get conversation details
  - `GET /api/users/{user_id}/conversations` - List user conversations
  - `PATCH /api/conversations/{id}` - Update conversation title
  - `DELETE /api/conversations/{id}` - Delete conversation

- Messages
  - `GET /api/conversations/{id}/messages` - Get conversation messages
  - `POST /api/chat` - Send message to AI agent

The backend then calls the agent service which uses:
- `CustomerSupportAgent.process_message(...)` - Main agent orchestration
- Tool registry for business logic
- Memory services for context
- RAG for knowledge retrieval

This maintains proper separation: UI → API → Agent → Services.

---

## Customer isolation design

The code enforces customer separation through multiple layers:

- JWT authentication ensures only authenticated users can access the API
- API endpoints validate JWT tokens and extract customer identity
- The backend validates conversation ownership before allowing access
- The UI displays only the authenticated user's conversations
- All database queries are scoped to the authenticated customer's ID

This defense-in-depth approach ensures security even if one layer fails. The backend JWT validation and ownership checks are the primary security boundaries.

---

## Conversation ID handling

The app correctly follows the persistent conversation model:

- a conversation is created in the backend via API
- a persistent `conversation_id` is generated and returned
- the UI stores only the active one in `st.session_state`
- messages are sent to the backend using that `conversation_id`
- SQLite remains the source of truth for the full conversation record

This is the correct architecture and should be kept unchanged.

---

## Implementation strengths

The current implementation includes comprehensive features:

- JWT-based authentication with secure token handling
- User registration and login with proper validation
- Conversation management (create, rename, delete, switch)
- Real-time chat interface with message history
- Customer session management and logout
- Database-backed persistence with soft delete
- Integration with FastAPI backend for all operations
- Error handling with user-friendly messages
- Responsive UI with proper state management
- Customer isolation and security at multiple layers

This represents a complete, production-ready implementation.

---

## Architecture highlights

### Agent Implementation

The AI agent (`app/agent/agent.py`) features:

- Tool-calling loop with max iteration protection
- Integration with Gemini 2.5 Flash
- Context building with short-term and long-term memory
- RAG integration for company knowledge
- Automatic memory extraction from conversations
- Graceful error handling and fallback responses

### Memory System

- **Short-term memory**: SQLite-based conversation history (last 10 messages)
- **Long-term memory**: Qdrant-based vector storage for user preferences
- **Memory extraction**: LLM-powered extraction of durable user information
- **Context building**: Combines both memory types for agent context

### Tool Registry

Secure tool mapping preventing arbitrary code execution:

- Order tools: status, cancellation, product search
- Product tools: inventory, stock checks
- Ticket tools: creation, status queries
- RAG tool: company knowledge retrieval

### Security Features

- JWT authentication with proper token validation
- Customer isolation at API and database levels
- Soft delete for data recovery
- Input validation and sanitization
- Error handling without exposing internals

---

## Known improvements for future consideration

While the system is fully functional, these enhancements could be considered:

1. **Rate limiting**: Add API rate limiting for abuse prevention
2. **Caching**: Implement response caching for common queries
3. **Monitoring**: Add logging and metrics for production monitoring
4. **Testing**: Expand test coverage for all components
5. **Documentation**: Add API documentation with Swagger/OpenAPI
6. **Deployment**: Create Docker configuration for easy deployment

---

## Final assessment

The project represents a complete, well-architected customer support AI system:

- Clean separation between UI, API, agent, and data layers
- Production-ready authentication and security
- Comprehensive business logic tools
- Sophisticated memory and RAG systems
- Modern, responsive user interface
- Proper error handling and user experience

The implementation demonstrates interview-ready Python backend skills with modern practices and architectural patterns.
