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
    get_current_customer,
    get_customers,
    get_messages,
    login_customer,
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
# Authentication state helpers
# -----------------------------------------------------------------------------
def _ensure_auth_state() -> None:
    """Initialize the authentication-related session state."""
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "customer" not in st.session_state:
        st.session_state.customer = None
    if "customer_id" not in st.session_state:
        st.session_state.customer_id = None


def login_user(email: str, password: str) -> bool:
    """Authenticate the user and store the JWT in session state."""
    try:
        login_result = login_customer(email.strip(), password)
    except ApiClientError as exc:
        st.error(str(exc))
        return False

    token = login_result.get("access_token")
    if not token:
        st.error("Login failed: no access token was provided.")
        return False

    try:
        customer = get_current_customer(token)
    except ApiClientError as exc:
        st.error(str(exc))
        return False

    st.session_state.access_token = token
    st.session_state.customer = customer
    st.session_state.customer_id = customer.get("id")
    st.session_state.conversation_id = None
    return True


def logout_user() -> None:
    """Clear authentication state and return to the login screen."""
    st.session_state.access_token = None
    st.session_state.customer = None
    st.session_state.customer_id = None
    st.session_state.conversation_id = None
    st.session_state.pop("active_customer_select", None)


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


@st.dialog("Delete chat?")
def confirm_delete_conversation(conversation_id: str, conversation_title: str) -> None:
    """Confirm and soft-delete a conversation."""
    st.write(f"This will delete **{conversation_title}**.")
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with delete_col:
        if st.button("Delete", type="primary", use_container_width=True):
            try:
                delete_conversation(conversation_id, st.session_state.customer_id, token=st.session_state.access_token)
                st.session_state.conversation_id = None
                st.session_state.open_conversation_actions = None
                st.rerun()
            except ApiClientError as exc:
                st.error(str(exc))


@st.dialog("Rename conversation")
def rename_conversation_dialog(conversation_id: str, current_title: str) -> None:
    """Rename a conversation from its action menu."""
    new_title = st.text_input("Conversation Title", value=current_title)
    if st.button("Save", type="primary", use_container_width=True):
        if new_title.strip():
            try:
                rename_conversation(
                    conversation_id,
                    st.session_state.customer_id,
                    new_title.strip(),
                    token=st.session_state.access_token,
                )
                st.rerun()
            except ApiClientError as exc:
                st.error(str(exc))


@st.dialog("Conversation actions")
def conversation_actions_dialog(conversation_id: str, conversation_title: str) -> None:
    """Show rename and delete actions without nesting dialogs."""
    action_mode = st.session_state.get("conversation_action_mode")

    if action_mode == f"rename:{conversation_id}":
        new_title = st.text_input("Conversation Title", value=conversation_title)
        if st.button("Save", type="primary", use_container_width=True):
            if new_title.strip():
                try:
                    rename_conversation(
                        conversation_id,
                        st.session_state.customer_id,
                        new_title.strip(),
                        token=st.session_state.access_token,
                    )
                    st.session_state.conversation_action_mode = None
                    st.rerun()
                except ApiClientError as exc:
                    st.error(str(exc))
        return

    if action_mode == f"delete:{conversation_id}":
        st.write(f"This will delete **{conversation_title}**.")
        cancel_col, delete_col = st.columns(2)
        with cancel_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.conversation_action_mode = None
                st.rerun(scope="fragment")
        with delete_col:
            if st.button("Delete", type="primary", use_container_width=True):
                try:
                    delete_conversation(conversation_id, st.session_state.customer_id, token=st.session_state.access_token)
                    if st.session_state.get("conversation_id") == conversation_id:
                        st.session_state.conversation_id = None
                    st.session_state.conversation_action_mode = None
                    st.rerun()
                except ApiClientError as exc:
                    st.error(str(exc))
        return

    if st.button("Rename", use_container_width=True):
        st.session_state.conversation_action_mode = f"rename:{conversation_id}"
        st.rerun(scope="fragment")
    if st.button("Delete", use_container_width=True):
        st.session_state.conversation_action_mode = f"delete:{conversation_id}"
        st.rerun(scope="fragment")


_ensure_auth_state()

if not st.session_state.access_token or not st.session_state.customer:
    st.title("Customer Support AI")
    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                if login_user(email, password):
                    st.rerun()

    st.stop()

# -----------------------------------------------------------------------------
# Sidebar: Customer-aware Conversation Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("💬 Customer Support AI")
customer = st.session_state.customer
st.sidebar.caption(f"Logged in as: {customer['name']} ({customer['email']})")
st.sidebar.button("Logout", use_container_width=True, on_click=logout_user)
st.sidebar.divider()
customer_map = {customer["id"]: customer}

if st.sidebar.button("➕ New Conversation", use_container_width=True, type="primary"):
    try:
        result = create_conversation(st.session_state.customer_id, title="New Conversation", token=st.session_state.access_token)
        if result.get("success"):
            st.session_state.conversation_id = result["conversation_id"]
            st.rerun()
        else:
            st.sidebar.error("Could not create conversation. Please try again.")
    except ApiClientError as exc:
        st.sidebar.error(str(exc))

st.sidebar.subheader("Conversations")

try:
    conversations = get_conversations(st.session_state.customer_id, token=st.session_state.access_token)
except ApiClientError as exc:
    logger.error(f"Error loading conversations: {exc}")
    conversations = []

if not conversations:
    st.sidebar.caption("No conversations yet for this customer.")
else:
    st.markdown(
        """
        <style>
        [class*="st-key-conversation_row_"] {
            background: #1f1f24;
            border: 1px solid #474751;
            border-radius: 12px;
            padding: 6px 8px;
            margin-bottom: 8px;
        }
        [class*="st-key-conversation_row_"] button {
            background: transparent;
            border: 0;
            box-shadow: none;
        }
        [class*="st-key-conversation_row_"] button:hover {
            background: #2b2b32;
            border: 0;
        }
        [class*="st-key-conversation_row_"] > div > div > div:first-child button {
            justify-content: flex-start;
        }
        [class*="st-key-sidebar_actions_"] button {
            color: #ffffff;
            font-size: 1.2rem;
            min-width: 36px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for conv in conversations:
        conv_id = conv["conversation_id"]
        conv_title = conv.get("title") or "New Conversation"
        with st.sidebar.container(key=f"conversation_row_{conv_id}"):
            conversation_col, actions_col = st.columns([9, 1])
            with conversation_col:
                if st.button(conv_title, key=f"conv_btn_{conv_id}", use_container_width=True):
                    st.session_state.conversation_id = conv_id
                    st.rerun()
            with actions_col:
                if st.button(
                    "",
                    icon=":material/more_horiz:",
                    key=f"sidebar_actions_{conv_id}",
                    help="Conversation actions",
                    use_container_width=True,
                ):
                    st.session_state.conversation_action_mode = None
                    conversation_actions_dialog(conv_id, conv_title)


# -----------------------------------------------------------------------------
# Main Chat Area
# -----------------------------------------------------------------------------
active_conv_id: Optional[str] = st.session_state.get("conversation_id")

if active_conv_id:
    try:
        active_conv_info = get_conversation(active_conv_id, token=st.session_state.access_token)
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
        if st.button(
            "⋯",
            key=f"main_actions_{active_conv_id}",
            help="Conversation actions",
        ):
            st.session_state.conversation_action_mode = None
            conversation_actions_dialog(active_conv_id, current_title)

    st.divider()

    try:
        messages_result = get_messages(active_conv_id, token=st.session_state.access_token)
        messages = messages_result
    except ApiClientError as exc:
        logger.error(f"Error loading messages: {exc}")
        messages = []

    if not messages:
        st.info("This is the beginning of your conversation. Ask about orders, policies, or products below.")
    else:
        for msg in messages:
            if msg.get("user_message"):
                with st.chat_message("user"):
                    st.markdown(msg["user_message"])
            if msg.get("response"):
                with st.chat_message("assistant"):
                    st.markdown(msg["response"])

else:
    active_customer = customer_map[st.session_state.customer_id]
    st.markdown(f"# Welcome to Customer Support, {active_customer['name']}!")
    st.markdown(
        """
        I am your local AI support assistant. I can help you with:

        - 📦 **Order Status**: Check tracking, delivery estimates, and current order states.
        - 🚫 **Order Cancellations**: Check if order can be cancelled.
        - 📋 **Company Policies**: Check refund, return, shipping, and warranty rules.
        - 🔍 **Product & Stock**: Verify product availability, specifications, and prices.
        - 🎫 **Support Tickets**: Open a new ticket, check existing ticket status.

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
            created = create_conversation(st.session_state.customer_id, title=derived_title, token=st.session_state.access_token)
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
                    token=st.session_state.access_token,
                )
                if response_data:
                    st.markdown(response_data.get("response", ""))
                else:
                    st.error("Sorry, I couldn't process your request right now. Please try again.")
            except ApiClientError as exc:
                logger.error(f"Unexpected API error: {exc}", exc_info=True)
                st.error("Sorry, I couldn't process your request right now. Please try again.")

