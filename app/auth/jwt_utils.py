"""JWT and password utility helpers for customer authentication."""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "customer-support-ai-dev-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    """Hash a plain-text password using PBKDF2 and a random salt."""
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{base64.b64encode(salt).decode('ascii')}:{base64.b64encode(derived).decode('ascii')}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify a supplied password against the stored password hash."""
    if not password or not stored_hash or ":" not in stored_hash:
        return False

    salt_b64, derived_b64 = stored_hash.split(":", 1)
    try:
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(derived_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(actual, expected)


def create_access_token(customer_id: str) -> str:
    """Create a signed JWT containing the authenticated customer UUID."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": customer_id, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode a JWT token."""
    if not token:
        raise ValueError("Missing token")
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (ExpiredSignatureError, InvalidTokenError, ValueError) as exc:
        raise ValueError("Invalid or expired JWT") from exc
