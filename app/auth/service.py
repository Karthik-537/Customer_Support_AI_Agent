"""Business logic for customer authentication."""

import logging

from fastapi import HTTPException, status

from app.api.schemas import CustomerSummary, LoginRequest, RegisterRequest, TokenResponse
from app.auth.jwt_utils import create_access_token, hash_password, verify_password
from app.database.db import SessionLocal
from app.database.models import Customer

logger = logging.getLogger(__name__)


def register_customer_account(payload: RegisterRequest) -> CustomerSummary:
    """Register a new customer account and return safe customer data."""
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
    if not payload.email.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    db = SessionLocal()
    try:
        existing = db.query(Customer).filter(Customer.email == payload.email.strip().lower()).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        customer = Customer(
            name=payload.name.strip(),
            email=payload.email.strip().lower(),
            password_hash=hash_password(payload.password),
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return CustomerSummary(id=customer.id, name=customer.name, email=customer.email)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to register customer")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not register customer") from exc
    finally:
        db.close()


def login_customer_account(payload: LoginRequest) -> TokenResponse:
    """Authenticate a customer by email and password and return a JWT."""
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == payload.email.strip().lower()).first()
        if customer is None or not verify_password(payload.password, customer.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        return TokenResponse(access_token=create_access_token(customer.id), token_type="bearer")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to login customer")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not log in") from exc
    finally:
        db.close()

