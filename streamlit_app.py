"""Streamlit frontend entrypoint for Customer Support AI Agent.

This module provides a clean, customer-facing chat UI that communicates with the
existing FastAPI backend instead of importing agent and database service logic.
"""

import logging
from typing import Optional

import streamlit as st

from app.frontend.api_client import (
    ApiClientError,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversations,
    get_customers,
    get_messages,
    rename_conversation,
    send_message,
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
# Frontend Helpers
# -----------------------------------------------------------------------------
def load_customers():
    """Load customer list from the API backend."""
    try:
        return get_customers()
    except ApiClientError as exc:
        logger.error(f"Error loading customers from API: {exc}")
        return []


# -----------------------------------------------------------------------------
# Sidebar: Customer Selection & Conversation Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("💬 Customer Support AI")

customers = load_customers()

if not customers:
    st.sidebar.error("No customers found in the backend.")
    st.sidebar.info("Ensure the FastAPI backend is running and the SQLite data has been seeded.")
    st.title("Customer Support AI")
    st.warning("No customer records are available from the API. Please start the backend and seed demo data first.")
    st.stop()

customer_map = {c["id"]: c for c in customers}
customer_ids = list(customer_map.keys())

if "customer_id" not in st.session_state or st.session_state.customer_id not in customer_map:
    st.session_state.customer_id = customer_ids[0]

current_index = customer_ids.index(st.session_state.customer_id)

st.sidebar.caption("Demo Customer Simulation")
selected_customer_id = st.sidebar.selectbox(
    "Active Customer",
    options=customer_ids,
    format_func=lambda cid: f"{customer_map[cid]['name']} ({customer_map[cid]['email']})",
    index=current_index,
    key="active_customer_select",
)

if selected_customer_id != st.session_state.customer_id:
    st.session_state.customer_id = selected_customer_id
    st.session_state.conversation_id = None
    st.rerun()

st.sidebar.divider()

if st.sidebar.button("➕ New Conversation", use_container_width=True, type="primary"):
    try:
        result = create_conversation(st.session_state.customer_id, title="New Conversation")
        if result.get("success"):
            st.session_state.conversation_id = result["conversation_id"]
            st.rerun()
        else:
            st.sidebar.error("Could not create conversation. Please try again.")
    except ApiClientError as exc:
        st.sidebar.error(str(exc))

st.sidebar.subheader("Conversations")

try:
    conversations = get_conversations(st.session_state.customer_id)
except ApiClientError as exc:
    logger.error(f"Error loading conversations: {exc}")
    conversations = []

if not conversations:
    st.sidebar.caption("No conversations yet for this customer.")
else:
    for conv in conversations:
        conv_id = conv["conversation_id"]
        conv_title = conv.get("title") or "New Conversation"
        is_active = st.session_state.get("conversation_id") == conv_id
        button_label = f"▶ {conv_title}" if is_active else f"💬 {conv_title}"
        if st.sidebar.button(button_label, key=f"conv_btn_{conv_id}", use_container_width=True):
            st.session_state.conversation_id = conv_id
            st.rerun()


# -----------------------------------------------------------------------------
# Main Chat Area
# -----------------------------------------------------------------------------
active_conv_id: Optional[str] = st.session_state.get("conversation_id")

if active_conv_id:
    try:
        active_conv_info = get_conversation(active_conv_id)
    except ApiClientError:
        st.session_state.conversation_id = None
        st.rerun()

    if not active_conv_info.get("success") or active_conv_info.get("user_id") != st.session_state.customer_id:
        st.session_state.conversation_id = None
        st.rerun()

    current_title = active_conv_info.get("title") or "New Conversation"

    header_col1, header_col2 = st.columns([5, 1])
    with header_col1:
        st.markdown(f"### 💬 {current_title}")
        st.caption(f"Customer: **{customer_map[st.session_state.customer_id]['name']}** | Conversation ID: `{active_conv_id}`")

    with header_col2:
        with st.popover("✏️ Rename"):
            new_title = st.text_input("Conversation Title", value=current_title, key=f"title_{active_conv_id}")
            if st.button("Save", key="save_title_btn", use_container_width=True):
                if new_title.strip():
                    try:
                        rename_conversation(active_conv_id, st.session_state.customer_id, new_title.strip())
                        st.rerun()
                    except ApiClientError as exc:
                        st.error(str(exc))

    st.divider()

    try:
        messages_result = get_messages(active_conv_id)
        messages = messages_result
    except ApiClientError as exc:
        logger.error(f"Error loading messages: {exc}")
        messages = []

    if not messages:
        st.info("This is the beginning of your conversation. Ask about orders, policies, or products below.")
    else:
        for msg in messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            with st.chat_message(role):
                st.markdown(content)

else:
    active_customer = customer_map[st.session_state.customer_id]
    st.markdown(f"# Welcome to Customer Support, {active_customer['name']}!")
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
    if not st.session_state.get("conversation_id"):
        derived_title = user_message.strip()[:35] + ("..." if len(user_message.strip()) > 35 else "")
        try:
            created = create_conversation(st.session_state.customer_id, title=derived_title)
            if created.get("success"):
                st.session_state.conversation_id = created["conversation_id"]
            else:
                st.error("Failed to start a new conversation. Please try again.")
                st.stop()
        except ApiClientError as exc:
            st.error(str(exc))
            st.stop()

    conversation_id = st.session_state.conversation_id

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("AI is thinking..."):
            try:
                response_data = send_message(
                    user_id=st.session_state.customer_id,
                    message=user_message,
                    conversation_id=conversation_id,
                )
                if response_data:
                    st.markdown(response_data.get("response", ""))
                else:
                    st.error("Sorry, I couldn't process your request right now. Please try again.")
            except ApiClientError as exc:
                logger.error(f"Unexpected API error: {exc}", exc_info=True)
                st.error("Sorry, I couldn't process your request right now. Please try again.")

    st.rerun()
