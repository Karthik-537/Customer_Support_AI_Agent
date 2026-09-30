"""Streamlit frontend entrypoint for Customer Support AI Agent.

This module provides a clean, customer-facing chat UI that communicates with the
existing FastAPI backend instead of importing agent and database service logic.
"""

import logging
import os
from typing import Optional

from streamlit_cookies_manager import EncryptedCookieManager
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
AUTH_COOKIE_NAME = "customer_access_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() == "true"
AUTH_COOKIE_LOGGED_OUT = "__customer_support_logged_out__"

# Changes every time the Streamlit process starts. This makes an old browser
# login invalid after the server is restarted, while still allowing a normal
# browser refresh to restore the login during the same server process.
@st.cache_resource(show_spinner=False)
def _get_server_session_id() -> str:
    """Return one ID for the lifetime of the Streamlit server process.

    Streamlit reruns this script for browser refreshes and widget interactions,
    so a plain module-level random value would change on every rerun. Caching
    the value as a resource keeps it stable across reruns while a server
    restart creates a new value and invalidates old browser auth cookies.
    """
    return os.urandom(16).hex()


SERVER_SESSION_ID = _get_server_session_id()

def _ensure_auth_state() -> None:
    if "access_token" not in st.session_state: st.session_state.access_token = None
    if "customer" not in st.session_state: st.session_state.customer = None
    if "customer_id" not in st.session_state: st.session_state.customer_id = None
    if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
    if "logout_completed" not in st.session_state: st.session_state.logout_completed = False

# IMPORTANT: Create the cookie manager at module level on every Streamlit run.
# The browser component needs to be rendered on each run so it can send the
# current browser cookies back to Python. Keeping the component object in
# st.session_state prevents that initialization cycle on a fresh session.
cookie_manager = EncryptedCookieManager(
    prefix="customer_support_ai/",
    password=os.getenv("COOKIES_PASSWORD", "change-this-cookie-secret"),
)

def _encode_auth_cookie(token: str) -> str:
    return f"{SERVER_SESSION_ID}:{token}"


def _decode_auth_cookie(value: str) -> tuple[Optional[str], Optional[str]]:
    if not value or ":" not in value:
        return None, None
    server_id, token = value.split(":", 1)
    return server_id or None, token or None


def _set_auth_cookie(token: str) -> None:
    cookie_manager[AUTH_COOKIE_NAME] = _encode_auth_cookie(token)
    cookie_manager.save()

CONVERSATION_COOKIE_NAME = "active_conversation_id"
HOME_SCREEN_MARKER = "__HOME__"


def _set_conversation_cookie(conversation_id: Optional[str]) -> None:
    """Persist the exact currently visible screen across browser refreshes."""
    try:
        # Persist an explicit home marker instead of deleting the cookie.
        # This prevents an older conversation value from being reused after
        # a rerun/refresh while the user is on the home screen.
        cookie_manager[CONVERSATION_COOKIE_NAME] = (
            conversation_id if conversation_id else HOME_SCREEN_MARKER
        )
        cookie_manager.save()
    except Exception:
        logger.exception("Failed to persist active conversation screen")


def _delete_conversation_cookie() -> None:
    # Preserve the existing call sites, but explicitly persist the home screen.
    _set_conversation_cookie(None)


def _delete_auth_cookie() -> None:
    """Delete the persisted authentication cookie immediately."""
    try:
        if not cookie_manager.ready():
            return

        # EncryptedCookieManager documents deletion through ``del``.
        # Using pop() here can leave the component's internal cookie map
        # unchanged, which causes the JWT to be restored on the next run.
        if AUTH_COOKIE_NAME in cookie_manager:
            del cookie_manager[AUTH_COOKIE_NAME]
        cookie_manager.save()
    except Exception:
        logger.exception("Failed to delete authentication cookie")


def _restore_auth_from_cookie() -> None:
    """Restore the exact authenticated screen after a browser refresh.

    The JWT is accepted only when it was issued for the current Streamlit
    process. Therefore a normal browser refresh keeps the user logged in,
    while restarting the Streamlit server forces a fresh login.
    """
    if st.session_state.access_token and st.session_state.customer:
        return

    raw_cookie = cookie_manager.get(AUTH_COOKIE_NAME)
    server_id, token = _decode_auth_cookie(raw_cookie)

    # A cookie from an older Streamlit process is never valid in this process.
    if server_id != SERVER_SESSION_ID or not token:
        return

    # Logout is represented by a durable marker rather than cookie deletion.
    # This prevents a stale browser cookie value from restoring the JWT.
    if token == AUTH_COOKIE_LOGGED_OUT:
        return

    try:
        customer = get_current_customer(token)
    except ApiClientError:
        return

    st.session_state.access_token = token
    st.session_state.customer = customer
    st.session_state.customer_id = customer.get("id")
    st.session_state.auth_mode = "login"

    # Restore the exact conversation that was visible before the browser
    # refresh. Validate it against the authenticated customer before using it.
    conversation_id = cookie_manager.get(CONVERSATION_COOKIE_NAME)
    st.session_state.conversation_id = None

    # If the user was on the main agent home screen before refresh, keep the
    # home screen. Do not fall back to an older conversation cookie.
    if conversation_id == HOME_SCREEN_MARKER:
        return

    if conversation_id:
        try:
            conversation = get_conversation(conversation_id, token=token)
            if (
                conversation.get("success")
                and conversation.get("user_id") == st.session_state.customer_id
            ):
                st.session_state.conversation_id = conversation_id
            else:
                _delete_conversation_cookie()
        except ApiClientError:
            _delete_conversation_cookie()


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
    st.session_state.logout_completed = False
    # Overwrite the logged-out marker with the new JWT. A fresh login starts
    # at the welcome screen, so no previous conversation is restored.
    _set_auth_cookie(token)
    _delete_conversation_cookie()
    return True


def register_user(name: str, email: str, password: str) -> bool:
    """Register a new customer account and redirect the user to login."""
    try:
        register_customer(name.strip(), email.strip(), password)
    except ApiClientError as exc:
        st.error(str(exc))
        return False

    _set_auth_cookie(AUTH_COOKIE_LOGGED_OUT)
    st.session_state.access_token = None
    st.session_state.customer = None
    st.session_state.customer_id = None
    st.session_state.conversation_id = None
    st.session_state.auth_mode = "login"
    st.success("Registration successful. Please sign in.")
    return True


def logout_user() -> None:
    """Clear authentication state and persist a logged-out marker."""
    # Do NOT delete the auth cookie here. The cookie component can report the
    # old browser value during the rerun immediately after logout. Instead,
    # overwrite the cookie with a durable logged-out marker. This uses the
    # same save path as login, so a stale JWT cannot be restored on the next
    # rerun or after a browser refresh.
    _set_auth_cookie(AUTH_COOKIE_LOGGED_OUT)

    st.session_state.access_token = None
    st.session_state.customer = None
    st.session_state.customer_id = None
    st.session_state.conversation_id = None
    st.session_state.auth_mode = "login"
    st.session_state.pop("active_customer_select", None)
    st.session_state.logout_completed = True
    _delete_conversation_cookie()


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


def _conversation_display_title(conv: dict, index: int) -> str:
    """Return a unique, useful title for a conversation history entry."""
    title = (conv.get("title") or "").strip()
    if title and title.lower() != "new conversation":
        return title
    return f"Conversation {index}"


def _title_from_first_message(message: str) -> str:
    """Create a short conversation title from the user's first message."""
    clean = " ".join(message.strip().split())
    if not clean:
        return "Conversation"
    return clean[:40] + ("..." if len(clean) > 40 else "")


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
                _delete_conversation_cookie()
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
        cancel_col, delete_col = st.columns([1, 1], gap="small")
        with cancel_col:
            with st.container(key="conversation_action_cancel_wrap"):
                if st.button(
                    "Cancel",
                    key="conversation_action_cancel",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.conversation_action_mode = None
                    st.rerun(scope="fragment")
        with delete_col:
            if st.button(
                "Delete",
                key="conversation_action_delete_confirm",
                type="primary",
                use_container_width=True,
            ):
                try:
                    delete_conversation(conversation_id, st.session_state.customer_id, token=st.session_state.access_token)
                    if st.session_state.get("conversation_id") == conversation_id:
                        st.session_state.conversation_id = None
                        _delete_conversation_cookie()
                        st.session_state.conversation_action_mode = None
                    st.rerun()
                except ApiClientError as exc:
                    st.error(str(exc))
        return

    with st.container(key="conversation_action_rename_wrap"):
        if st.button(
            "Rename",
            key="conversation_action_rename",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.conversation_action_mode = f"rename:{conversation_id}"
            st.rerun(scope="fragment")

    with st.container(key="conversation_action_delete_wrap"):
        if st.button(
            "Delete",
            key="conversation_action_delete",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.conversation_action_mode = f"delete:{conversation_id}"
            st.rerun(scope="fragment")


_ensure_auth_state()
# Wait for the browser cookie component to initialize before making the
# authentication decision. This is the documented cookie-manager pattern.
if not cookie_manager.ready():
    st.stop()

# A logout callback clears the current Streamlit session. The logged-out
# marker in the cookie prevents the JWT from being restored on the rerun.
if not st.session_state.get("logout_completed", False):
    _restore_auth_from_cookie()
else:
    st.session_state.logout_completed = False

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
# Agent Screen Styling
# NOTE: This CSS is intentionally placed after the authentication branch.
# It affects only the authenticated agent screen.
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Agent page background */
    html, body, [data-testid="stAppViewContainer"], .stApp, section.main {
        background: #0e1017 !important;
        color: #f8fafc !important;
    }

    .block-container {
        max-width: 100% !important;
        padding-top: 2rem !important;
        padding-bottom: 0 !important;
        background: #0e1017 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #272833 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: #272833 !important;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    [data-testid="stSidebar"] .logged-in-email {
        color: #9ca3af !important;
        margin-top: -8px;
        margin-bottom: 16px;
    }

    /* Logout */
    [data-testid="stSidebar"] [class*="st-key-agent_logout"] button {
        width: 82px !important;
        min-width: 82px !important;
        height: 48px !important;
        min-height: 48px !important;
        border-radius: 10px !important;
        background: #2563eb !important;
        border: 1px solid #2563eb !important;
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    [data-testid="stSidebar"] [class*="st-key-agent_logout"] button:hover {
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
    }

    /* New conversation */
    [data-testid="stSidebar"] [class*="st-key-agent_new_conversation"] button {
        width: 100% !important;
        min-height: 50px !important;
        border-radius: 10px !important;
        background: #ff4b4b !important;
        border: 1px solid #ff4b4b !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] [class*="st-key-agent_new_conversation"] button:hover {
        background: #ff5c5c !important;
        border-color: #ff5c5c !important;
    }

    /* Conversation cards from the original agent screen */
    /* Conversation history: one visible bar per conversation. */
    [class*="st-key-conversation_row_"] {
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        min-height: 63px !important;
        box-sizing: border-box !important;
        background: #0e1117 !important;
        border: 1px solid #0e1117 !important;
        border-radius: 12px !important;
        padding: 0 8px !important;
        margin-bottom: 8px !important;
        overflow: hidden !important;
    }

    [class*="st-key-conversation_row_"] > div {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* The title button is transparent so it does not create a second bar. */
    [class*="st-key-conversation_row_"] [class*="st-key-conversation_title_"] {
        width: 100% !important;
        max-width: 100% !important;
    }

    [class*="st-key-conversation_row_"] [class*="st-key-conversation_title_"] > div {
        width: 100% !important;
        max-width: 100% !important;
    }

    [class*="st-key-conversation_row_"] [class*="st-key-conversation_title_"] button {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        height: 63px !important;
        min-height: 63px !important;
        box-sizing: border-box !important;
        justify-content: flex-start !important;
        padding: 0 12px !important;
        border-radius: 8px !important;
        background: transparent !important;
        border: 0 !important;
        color: #ffffff !important;
        box-shadow: none !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
    }

    [class*="st-key-conversation_row_"] [class*="st-key-conversation_title_"] button:hover {
        background: #2b3748 !important;
        border: 0 !important;
    }

    [class*="st-key-conversation_row_"] button {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    [class*="st-key-conversation_row_"] button:hover {
        background: #2b3748 !important;
        border: 0 !important;
    }

    [class*="st-key-conversation_row_"] > div > div > div:first-child button {
        justify-content: flex-start !important;
    }

    /* Conversation action buttons: wide enough for their full labels. */
    [class*="st-key-conversation_action_rename_wrap"],
    [class*="st-key-conversation_action_delete_wrap"] {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 0 12px 0 !important;
    }

    [class*="st-key-conversation_action_rename_wrap"] > div,
    [class*="st-key-conversation_action_delete_wrap"] > div {
        width: 100% !important;
        max-width: 100% !important;
    }

    [class*="st-key-conversation_action_rename_wrap"] button,
    [class*="st-key-conversation_action_delete_wrap"] button {
        display: flex !important;
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        height: 64px !important;
        min-height: 64px !important;
        box-sizing: border-box !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 10px !important;
        padding: 0 20px !important;
        font-size: 1.05rem !important;
        background: #1f2937 !important;
        border: 1px solid #1f2937 !important;
        color: #ffffff !important;
        white-space: nowrap !important;
    }

    [class*="st-key-conversation_action_rename_wrap"] button:hover,
    [class*="st-key-conversation_action_delete_wrap"] button:hover {
        background: #273449 !important;
        border-color: #273449 !important;
        color: #ffffff !important;
    }

    /* Delete dialog: Cancel must have the same dimensions as Delete. */
    [class*="st-key-conversation_action_cancel_wrap"] {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
    }

    [class*="st-key-conversation_action_cancel_wrap"] > div {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }

    [class*="st-key-conversation_action_cancel_wrap"] button {
        display: flex !important;
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    [class*="st-key-conversation_action_cancel_wrap"] button {
        height: 64px !important;
        min-height: 64px !important;
        border-radius: 10px !important;
        padding: 0 20px !important;
        font-size: 1.05rem !important;
        background: #1f2937 !important;
        border: 1px solid #1f2937 !important;
        color: #ffffff !important;
        white-space: nowrap !important;
    }

    /* Delete confirmation button: exactly the same dimensions as Cancel. */
    [class*="st-key-conversation_action_delete_confirm"] button {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        height: 64px !important;
        min-height: 64px !important;
        max-height: 64px !important;
        box-sizing: border-box !important;
        border-radius: 10px !important;
        padding: 0 20px !important;
        font-size: 1.05rem !important;
        background: #ff4b4b !important;
        border: 1px solid #ff4b4b !important;
        color: #ffffff !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [class*="st-key-conversation_action_delete_confirm"] button:hover {
        background: #ff5c5c !important;
        border-color: #ff5c5c !important;
        color: #ffffff !important;
    }

    [class*="st-key-conversation_action_cancel_wrap"] button:hover {
        background: #273449 !important;
        border-color: #273449 !important;
        color: #ffffff !important;
    }

    [class*="st-key-sidebar_actions_"] {
        height: 63px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }

    [class*="st-key-sidebar_actions_"] > div {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [class*="st-key-sidebar_actions_"] button {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        min-width: 36px !important;
        width: 36px !important;
        height: 36px !important;
        min-height: 36px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Main agent content */
    section.main h1,
    section.main h2,
    section.main h3,
    section.main p,
    section.main li,
    section.main div {
        /* Keep Streamlit's normal typography; only set the page foreground. */
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background: #272833 !important;
        border: 1px solid #272833 !important;
        border-radius: 10px !important;
    }

    [data-testid="stChatInput"] textarea {
        background: #272833 !important;
        color: #f8fafc !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #9ca3af !important;
    }

    [data-testid="stChatInput"] button {
        background: #3a3b45 !important;
        color: #d1d5db !important;
        border: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Sidebar: Customer-aware Conversation Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("💬 Customer Support AI")

customer = st.session_state.customer
customer_map = {customer["id"]: customer}

st.sidebar.caption(f"Logged in as: {customer['name']}")
st.sidebar.markdown(
    f'<div class="logged-in-email">({customer["email"]})</div>',
    unsafe_allow_html=True,
)

if st.sidebar.button(
    "Logout",
    use_container_width=False,
    key="agent_logout",
):
    logout_user()
    st.rerun()

st.sidebar.divider()

if st.sidebar.button(
    "➕ New Conversation",
    use_container_width=True,
    type="primary",
    key="agent_new_conversation",
):
    try:
        result = create_conversation(
            st.session_state.customer_id,
            title="New Conversation",
            token=st.session_state.access_token,
        )
        if result.get("success"):
            st.session_state.conversation_id = result["conversation_id"]
            _set_conversation_cookie(st.session_state.conversation_id)
            st.rerun()
        else:
            st.sidebar.error("Could not create conversation. Please try again.")
    except ApiClientError as exc:
        st.sidebar.error(str(exc))

st.sidebar.subheader("Conversations")

try:
    conversations = get_conversations(
        st.session_state.customer_id,
        token=st.session_state.access_token,
    )
except ApiClientError as exc:
    logger.error(f"Error loading conversations: {exc}")
    conversations = []

if not conversations:
    st.sidebar.caption("No conversations yet for this customer.")
else:
    for index, conv in enumerate(conversations, start=1):
        conv_id = conv["conversation_id"]
        conv_title = _conversation_display_title(conv, index)

        with st.sidebar.container(key=f"conversation_row_{conv_id}"):
            conversation_col, actions_col = st.columns([9, 1])

            with conversation_col:
                with st.container(key=f"conversation_title_{conv_id}"):
                    if st.button(
                        conv_title,
                        key=f"conv_btn_{conv_id}",
                        use_container_width=True,
                    ):
                        st.session_state.conversation_id = conv_id
                        _set_conversation_cookie(conv_id)
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
        _delete_conversation_cookie()
        st.rerun()

    if not active_conv_info.get("success") or active_conv_info.get("user_id") != st.session_state.customer_id:
        st.session_state.conversation_id = None
        _delete_conversation_cookie()
        st.rerun()

    current_title = (active_conv_info.get("title") or "").strip() or "Conversation"

    header_col1, header_col2 = st.columns([5, 1])
    with header_col1:
        st.markdown(f"### 💬 {current_title}")
        st.caption(f"Customer: **{customer_map[st.session_state.customer_id]['name']}**")

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
        - 🚫 **Order Cancellations**: Check whether an order can be cancelled.
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
                _set_conversation_cookie(st.session_state.conversation_id)
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

                    # Give a newly-created/default conversation a meaningful
                    # title based on its first customer message. Existing
                    # custom/renamed titles are left untouched.
                    try:
                        active_info = get_conversation(
                            conversation_id,
                            token=st.session_state.access_token,
                        )
                        existing_title = (active_info.get("title") or "").strip()
                        if existing_title.lower() in {"", "new conversation"}:
                            try:
                                rename_conversation(
                                    conversation_id,
                                    st.session_state.customer_id,
                                    _title_from_first_message(user_message),
                                    token=st.session_state.access_token,
                                )
                            except ApiClientError as exc:
                                # Title generation must never break an otherwise
                                # successful chat response.
                                logger.warning("Could not auto-title conversation: %s", exc)
                    except ApiClientError as exc:
                        logger.warning("Could not inspect conversation title: %s", exc)
                else:
                    st.error("Sorry, I couldn't process your request right now. Please try again.")
            except ApiClientError as exc:
                logger.error(f"Unexpected API error: {exc}", exc_info=True)
                st.error("Sorry, I couldn't process your request right now. Please try again.")
