"""Streamlit frontend entrypoint for Customer Support AI Agent.

This module provides a clean, customer-facing chat UI backed by the existing
CustomerSupportAgent, SQLite database, and Qdrant memory services.
"""

import logging
from typing import List, Optional

import streamlit as st

from app.agent.agent import CustomerSupportAgent, get_agent
from app.database.db import SessionLocal, init_db
from app.database.models import Customer
from app.memory.conversation_memory import (
    create_conversation,
    get_conversation,
    get_messages,
    list_user_conversations,
    update_conversation,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Support AI",
    page_icon="💬",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Backend Helper Functions (Presentation Layer Data Access)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_support_agent() -> CustomerSupportAgent:
    """Retrieve and cache the CustomerSupportAgent instance."""
    return get_agent()


def load_customers() -> List[Customer]:
    """Retrieve all customers from SQLite to populate the demo selector."""
    db = SessionLocal()
    try:
        return db.query(Customer).order_by(Customer.id).all()
    except Exception as e:
        logger.error(f"Error loading customers from SQLite: {e}")
        return []
    finally:
        db.close()


def ensure_database_initialized() -> None:
    """Ensure database tables exist on startup."""
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database initialization check warning: {e}")


# Initialize DB tables if needed
ensure_database_initialized()


# -----------------------------------------------------------------------------
# Sidebar: Customer Selection & Conversation Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("💬 Customer Support AI")

# Load existing customers from the database
customers = load_customers()

if not customers:
    st.sidebar.error("No customers found in database.")
    st.sidebar.info("Run database seed script to populate demo data:\n`python -m app.database.seed`")
    st.title("Customer Support AI")
    st.warning("Database contains no customer records. Please seed demo data first.")
    st.stop()

# Build mapping of customer_id -> Customer object
customer_map = {c.id: c for c in customers}
customer_ids = list(customer_map.keys())

# Initialize customer_id in session state if missing
if "customer_id" not in st.session_state or st.session_state.customer_id not in customer_map:
    st.session_state.customer_id = customer_ids[0]

# Determine default selector index
current_index = customer_ids.index(st.session_state.customer_id)

st.sidebar.caption("Demo Customer Simulation")
selected_customer_id = st.sidebar.selectbox(
    "Active Customer",
    options=customer_ids,
    format_func=lambda cid: f"{customer_map[cid].name} ({customer_map[cid].email})",
    index=current_index,
    key="active_customer_select",
)

# Step 13 & 24: Customer Switching and Isolation
if selected_customer_id != st.session_state.customer_id:
    st.session_state.customer_id = selected_customer_id
    st.session_state.conversation_id = None
    st.rerun()

st.sidebar.divider()

# + New Conversation Button
if st.sidebar.button("➕ New Conversation", use_container_width=True, type="primary"):
    res = create_conversation(st.session_state.customer_id, title="New Conversation")
    if res.get("success"):
        st.session_state.conversation_id = res["conversation_id"]
        st.rerun()
    else:
        st.sidebar.error("Could not create conversation. Please try again.")

# Conversation List (Belonging ONLY to selected customer, sorted updated_at DESC)
conv_res = list_user_conversations(st.session_state.customer_id)
conversations = conv_res.get("conversations", []) if conv_res.get("success") else []

st.sidebar.subheader("Conversations")

if not conversations:
    st.sidebar.caption("No conversations yet for this customer.")
else:
    for conv in conversations:
        conv_id = conv["conversation_id"]
        conv_title = conv.get("title") or "New Conversation"
        is_active = (st.session_state.get("conversation_id") == conv_id)

        # Highlight currently active conversation
        button_label = f"▶ {conv_title}" if is_active else f"💬 {conv_title}"
        if st.sidebar.button(button_label, key=f"conv_btn_{conv_id}", use_container_width=True):
            st.session_state.conversation_id = conv_id
            st.rerun()


# -----------------------------------------------------------------------------
# Main Chat Area
# -----------------------------------------------------------------------------
active_conv_id: Optional[str] = st.session_state.get("conversation_id")

if active_conv_id:
    # Verify ownership before displaying
    active_conv_info = get_conversation(active_conv_id)
    if not active_conv_info.get("success") or active_conv_info.get("user_id") != st.session_state.customer_id:
        st.session_state.conversation_id = None
        st.rerun()

    current_title = active_conv_info.get("title") or "New Conversation"

    # Header and Rename controls
    header_col1, header_col2 = st.columns([5, 1])
    with header_col1:
        st.markdown(f"### 💬 {current_title}")
        st.caption(f"Customer: **{customer_map[st.session_state.customer_id].name}** | Conversation ID: `{active_conv_id}`")

    with header_col2:
        with st.popover("✏️ Rename"):
            new_title = st.text_input("Conversation Title", value=current_title, key=f"title_{active_conv_id}")
            if st.button("Save", key="save_title_btn", use_container_width=True):
                if new_title.strip():
                    update_conversation(active_conv_id, title=new_title.strip())
                    st.rerun()

    st.divider()

    # Load and render message history from SQLite (Single Source of Truth)
    messages_result = get_messages(active_conv_id)
    messages = messages_result.get("messages", []) if messages_result.get("success") else []

    if not messages:
        st.info("This is the beginning of your conversation. Ask about orders, policies, or products below.")
    else:
        for msg in messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            with st.chat_message(role):
                st.markdown(content)

else:
    # Step 18: Empty State / Welcome Screen
    active_customer = customer_map[st.session_state.customer_id]
    st.markdown(f"# Welcome to Customer Support, {active_customer.name}!")
    st.markdown(
        """
        I am your local AI support assistant. I can help you with:

        - 📦 **Order Status**: Check tracking, delivery estimates, and current order states.
        - 🚫 **Order Cancellations**: Request cancellations for eligible pending orders.
        - 📋 **Company Policies**: Check refund, return, shipping, and warranty rules.
        - 🔍 **Inventory & Stock**: Verify product availability, specifications, and prices.
        - 🎫 **Support Tickets**: Open a new ticket, check existing ticket status, or request escalation.

        ---
        👉 **To get started**, select a past conversation from the sidebar, click **➕ New Conversation**, or simply type your message below.
        """
    )


# -----------------------------------------------------------------------------
# Chat Input & Agent Dispatch
# -----------------------------------------------------------------------------
user_message = st.chat_input("How can we help you today?")

if user_message:
    # If no conversation was selected, create one automatically
    if not st.session_state.get("conversation_id"):
        derived_title = user_message.strip()[:35] + ("..." if len(user_message.strip()) > 35 else "")
        created = create_conversation(st.session_state.customer_id, title=derived_title)
        if created.get("success"):
            st.session_state.conversation_id = created["conversation_id"]
        else:
            st.error("Failed to start a new conversation. Please try again.")
            st.stop()

    conversation_id = st.session_state.conversation_id

    # Display user turn in UI immediately
    with st.chat_message("user"):
        st.markdown(user_message)

    # Process response through existing backend agent
    with st.chat_message("assistant"):
        with st.spinner("AI is thinking..."):
            agent = get_support_agent()
            try:
                response_data = agent.process_message(
                    user_message=user_message,
                    user_id=st.session_state.customer_id,
                    conversation_id=conversation_id,
                )

                if response_data.get("success"):
                    st.markdown(response_data.get("response", ""))
                else:
                    error_msg = (
                        response_data.get("response")
                        or response_data.get("error")
                        or "Sorry, I couldn't process your request right now. Please try again."
                    )
                    st.error(error_msg)

            except Exception as e:
                logger.error(f"Unexpected error executing agent: {e}", exc_info=True)
                st.error("Sorry, I couldn't process your request right now. Please try again.")

    # Step 23: Refresh from SQLite so the UI accurately displays persisted messages
    st.rerun()
