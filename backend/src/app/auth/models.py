"""Authentication models for user accounts."""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.storage.db import Base


class AuthProvider(str, Enum):
    """Authentication provider types."""
    LOCAL = "local"          # Email/password (public frontend)
    ZITADEL = "zitadel"      # Zitadel OIDC (SalesAI integration)
    GOOGLE = "google"        # Google OAuth
    GITHUB = "github"        # GitHub OAuth


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"            # Limited features
    PRO = "pro"              # Standard features
    ENTERPRISE = "enterprise"  # All features


class UserAccount(Base):
    """User account for Scripe platform.

    Supports multiple auth providers and credit-based billing.
    """
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True)

    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)

    # Auth
    auth_provider = Column(SQLEnum(AuthProvider), default=AuthProvider.LOCAL)
    external_id = Column(String(255), nullable=True, index=True)  # Zitadel/OAuth ID
    password_hash = Column(String(255), nullable=True)  # Only for LOCAL auth
    email_verified = Column(Boolean, default=False)

    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_expires_at = Column(DateTime, nullable=True)

    # Credits
    credits_balance = Column(Float, default=0.0)
    credits_used_total = Column(Float, default=0.0)

    # Settings
    settings_json = Column(Text, nullable=True)  # JSON user preferences
    default_country = Column(String(2), default="IT")
    default_language = Column(String(5), default="it")

    # Company / Billing Info
    company_name = Column(String(255), nullable=True)
    vat_id = Column(String(50), nullable=True)  # USt-IdNr. / VAT ID
    tax_exempt = Column(Boolean, default=False)
    billing_email = Column(String(255), nullable=True)  # Separate billing email

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    searches = relationship("UserSearch", back_populates="user")
    saved_lists = relationship("SavedList", back_populates="user")
    billing_addresses = relationship("BillingAddress", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")

    def __repr__(self):
        return f"<UserAccount(id={self.id}, email={self.email}, provider={self.auth_provider})>"

    @property
    def settings(self) -> dict:
        """Get parsed settings."""
        import json
        if self.settings_json:
            return json.loads(self.settings_json)
        return {}

    @settings.setter
    def settings(self, value: dict):
        """Set settings."""
        import json
        self.settings_json = json.dumps(value)


class CreditTransaction(Base):
    """Credit transaction record."""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)

    # Transaction details
    amount = Column(Float, nullable=False)  # Positive = credit, Negative = debit
    balance_after = Column(Float, nullable=False)
    operation = Column(String(50), nullable=False)  # purchase, search, refund, bonus

    # Reference
    search_id = Column(Integer, nullable=True)  # Link to search if applicable
    description = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=True)

    # Expiration (NULL = never expires, e.g. purchased credits)
    expires_at = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserAccount", back_populates="credit_transactions")

    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, user={self.user_id}, amount={self.amount})>"


class UserSearch(Base):
    """User's search history."""
    __tablename__ = "user_searches"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=False)

    # Credits spent
    credits_spent = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserAccount", back_populates="searches")


class ProcessedWebhookEvent(Base):
    """Tracks processed webhook events for idempotency.

    Prevents duplicate processing of webhook events (e.g., Stripe payments).
    Stored in database to survive server restarts and work across multiple processes.
    """
    __tablename__ = "processed_webhook_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # e.g., "checkout.session.completed"
    source = Column(String(50), nullable=False)  # e.g., "stripe"
    processed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ProcessedWebhookEvent(id={self.event_id}, type={self.event_type})>"


class SavedList(Base):
    """User's saved lead lists."""
    __tablename__ = "saved_lists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)

    # List details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Content (JSON array of company IDs or embedded data)
    companies_json = Column(Text, nullable=True)
    company_count = Column(Integer, default=0)

    # Source search
    source_search_id = Column(Integer, nullable=True)

    # Sharing
    is_public = Column(Boolean, default=False)
    share_token = Column(String(64), nullable=True, unique=True)

    # Status
    is_archived = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserAccount", back_populates="saved_lists")

    def __repr__(self):
        return f"<SavedList(id={self.id}, name={self.name}, count={self.company_count})>"


# Pydantic models for API
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User data for API responses."""
    id: int
    email: str
    name: str | None
    auth_provider: AuthProvider
    subscription_tier: SubscriptionTier
    credits_balance: float
    is_active: bool
    created_at: datetime

    # Company / Billing Info
    company_name: str | None = None
    vat_id: str | None = None
    tax_exempt: bool = False
    billing_email: str | None = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation request."""
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)
    name: str | None = None


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User
