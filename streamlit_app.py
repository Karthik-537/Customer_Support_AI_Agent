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
    register_customer,
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
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"


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
    st.session_state.auth_mode = "login"
    return True


def register_user(name: str, email: str, password: str) -> bool:
    """Register a new customer account and redirect the user to login."""
    try:
        register_customer(name.strip(), email.strip(), password)
    except ApiClientError as exc:
        st.error(str(exc))
        return False

    st.session_state.access_token = None
    st.session_state.customer = None
    st.session_state.customer_id = None
    st.session_state.conversation_id = None
    st.session_state.auth_mode = "login"
    st.success("Registration successful. Please sign in.")
    return True


def logout_user() -> None:
    """Clear authentication state and return to the login screen."""
    st.session_state.access_token = None
    st.session_state.customer = None
    st.session_state.customer_id = None
    st.session_state.conversation_id = None
    st.session_state.auth_mode = "login"
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

st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], .stApp, section.main {
        background: #ffffff !important;
        color: #111827 !important;
    }
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] {
        display: none !important;
        background: transparent !important;
    }
    .block-container {
        max-width: 100% !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin: 0 !important;
        background: #ffffff !important;
    }
    .auth-shell {
        width: 100%;
        display: flex;
        align-items: flex-start;
        justify-content: center;
        padding: 0;
        margin: 0;
    }
    .auth-card {
        width: min(100%, 1200px);
        background: transparent;
        border: none;
        border-radius: 0;
        box-shadow: none;
        padding: 0;
        margin: 0;
    }
    .brand {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -0.065em;
        color: #0f172a;
        margin: 0 auto 32px;
    }
    .brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        font-size: 1.55rem;
        color: #2563eb;
        line-height: 1;
    }
    .auth-title {
        text-align: left;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.04em;
        color: #111827;
        margin-bottom: 4px;
    }
    .auth-subtitle {
        text-align: left;
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 22px;
    }
    .auth-form label {
        font-size: 0.95rem !important;
        color: #111827 !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stTextInputRoot"] {
        width: 100% !important;
        margin-bottom: 0 !important;
    }
    [data-testid="stTextInputRoot"] > div {
        background: #1f2937 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 12px !important;
        min-height: 60px !important;
        box-shadow: none !important;
        overflow: hidden !important;
    }
    [data-testid="stTextInputRoot"] input {
        background: transparent !important;
        color: #f8fafc !important;
        font-size: 1.05rem !important;
        padding: 0.9rem 1rem !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        min-height: 60px !important;
    }
    [data-testid="stTextInputRoot"] input::placeholder {
        color: rgba(255, 255, 255, 0.7) !important;
        opacity: 1 !important;
        font-size: 1.05rem !important;
    }
    [data-testid="stTextInputRoot"] input:focus {
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    [data-testid="stBaseButton-secondary"] > button,
    .stButton > button[kind="secondary"] {
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        height: 58px !important;
        min-height: 58px !important;
        padding: 0 !important;
        border-radius: 12px !important;
        border: 1px solid #1f2937 !important;
        background: #1f2937 !important;
        color: #ffffff !important;
        font-size: 1.2rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 0 0 10px !important;
        box-shadow: none !important;
    }
    .stCheckbox > label {
        color: #111827 !important;
        font-size: 1rem !important;
    }
    .stCheckbox > label > span {
        color: #111827 !important;
    }
    .stCheckbox [role="checkbox"] {
        border: 1px solid #111827 !important;
        background: #ffffff !important;
    }
    .auth-form .stButton > button,
    .auth-form .stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button,
    form button[type="submit"] {
        width: 100% !important;
        border-radius: 10px !important;
        border: 1px solid #2563eb !important;
        background: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        height: 50px !important;
        min-height: 50px !important;
        font-size: 1rem !important;
        box-shadow: none !important;
    }

    .auth-form .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    form button[type="submit"]:hover {
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
        color: #ffffff !important;
    }

    /* Account switch buttons: same width/height/color as the Sign In button. */
    .auth-switch-form button,
    div[data-testid="stFormSubmitButton"] > button {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        height: 50px !important;
        min-height: 50px !important;
        border-radius: 10px !important;
        border: 1px solid #2563eb !important;
        background: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: none !important;
        padding: 0.75rem 1rem !important;
    }

    .auth-switch-form button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
        color: #ffffff !important;
    }

    .auth-toggle {
        text-align: center;
        margin-top: 18px;
        font-size: 0.98rem;
        color: #4b5563;
    }
    .auth-toggle button {
        background: none;
        border: none;
        color: #2563eb;
        font-weight: 600;
        cursor: pointer;
        padding: 0;
    }
    div[data-testid="stVerticalBlock"] > div {
        gap: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.access_token or not st.session_state.customer:
    auth_mode = st.session_state.get("auth_mode", "login")
    auth_container = st.container()
    with auth_container:
        st.markdown('<div class="auth-shell"><div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="brand"><span class="brand-mark">🤖</span> Customer Support Agent</div>', unsafe_allow_html=True)

        if auth_mode == "login":
            st.markdown('<div class="auth-title">Welcome back</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-subtitle">Sign in to your support account</div>', unsafe_allow_html=True)

            email = st.text_input("Email", placeholder="Enter your email", label_visibility="visible")
            password_value = st.text_input(
                "Password",
                type="default" if st.session_state.get("show_password", False) else "password",
                placeholder="Enter your password",
                label_visibility="visible",
            )

            with st.form("login_form", clear_on_submit=False):
                st.markdown('<div class="auth-form">', unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if submitted:
                    if not email or not password_value:
                        st.error("Email and password are required.")
                    else:
                        if login_user(email, password_value):
                            st.rerun()

            st.markdown('<div class="auth-toggle">Don\'t have an account?</div>', unsafe_allow_html=True)
            with st.form("register_switch_form", clear_on_submit=False):
                switch_register = st.form_submit_button("Register", use_container_width=True)
                if switch_register:
                    st.session_state.auth_mode = "register"
                    st.rerun()

        else:
            st.markdown('<div class="auth-title">Create your account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-subtitle">Get started with customer support</div>', unsafe_allow_html=True)

            name = st.text_input("Name", placeholder="Enter your name", label_visibility="visible")
            email = st.text_input("Email", placeholder="Enter your email", label_visibility="visible")
            password_value = st.text_input(
                "Password",
                type="default" if st.session_state.get("show_password", False) else "password",
                placeholder="Enter your password",
                label_visibility="visible",
            )

            with st.form("register_form", clear_on_submit=False):
                st.markdown('<div class="auth-form">', unsafe_allow_html=True)
                submitted = st.form_submit_button("Register", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if submitted:
                    if not name or not email or not password_value:
                        st.error("Name, email, and password are required.")
                    else:
                        if register_user(name, email, password_value):
                            st.rerun()

            st.markdown('<div class="auth-toggle">Already have an account?</div>', unsafe_allow_html=True)
            with st.form("login_switch_form", clear_on_submit=False):
                switch_login = st.form_submit_button("Sign In", use_container_width=True)
                if switch_login:
                    st.session_state.auth_mode = "login"
                    st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)
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
