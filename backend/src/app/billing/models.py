"""Billing models for addresses and invoices."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from app.storage.db import Base


class BillingAddress(Base):
    """Billing address for a user."""
    __tablename__ = "billing_addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)

    # Address fields
    street_address = Column(String(255), nullable=False)
    street_address_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(2), nullable=False)  # ISO 3166-1 alpha-2

    # Status
    is_primary = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("UserAccount", back_populates="billing_addresses")

    def __repr__(self):
        return f"<BillingAddress(id={self.id}, user_id={self.user_id}, city={self.city})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "street_address": self.street_address,
            "street_address_2": self.street_address_2,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "country": self.country,
        }


class InvoiceStatus(str, Enum):
    """Invoice status types."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Invoice for a purchase."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)

    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)

    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=0)  # e.g., 19.00 for 19%
    tax_amount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="EUR")

    # Status
    status = Column(String(20), default=InvoiceStatus.PAID.value)

    # Stripe references
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_checkout_session_id = Column(String(255), nullable=True)

    # Details (JSON)
    items_json = Column(Text, nullable=True)  # JSON: [{description, quantity, unit_price, amount}]
    billing_address_snapshot = Column(Text, nullable=True)  # JSON snapshot at time of invoice
    customer_snapshot = Column(Text, nullable=True)  # JSON: {name, email, company_name, vat_id}
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("UserAccount", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, total={self.total})>"


# Pydantic models for API

class BillingAddressCreate(BaseModel):
    """Request to create/update billing address."""
    street_address: str = Field(..., min_length=1, max_length=255)
    street_address_2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state_province: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=2)


class BillingAddressResponse(BaseModel):
    """Billing address response."""
    id: int
    street_address: str
    street_address_2: str | None
    city: str
    state_province: str | None
    postal_code: str
    country: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceItemResponse(BaseModel):
    """Invoice line item."""
    description: str
    quantity: int
    unit_price: float
    amount: float


class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: int
    invoice_number: str
    invoice_date: datetime
    due_date: datetime | None

    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    currency: str

    status: str
    items: list[InvoiceItemResponse] = []

    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """List of invoices response."""
    items: list[InvoiceResponse]
    total: int
