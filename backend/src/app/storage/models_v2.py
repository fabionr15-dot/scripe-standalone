"""Extended database models with Clients and Campaigns hierarchy."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Client(Base):
    """Client/Customer entity - top level."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settings
    settings_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}')>"


class Campaign(Base):
    """Campaign/Project for a client - can have multiple searches."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Campaign configuration
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Contains: target_industries, countries, languages, company_size_range, etc.

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )  # draft, active, paused, completed, archived

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="campaigns")
    searches: Mapped[list["Search"]] = relationship(
        "Search", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class Search(Base):
    """Search execution within a campaign."""

    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Validation settings (toggleable)
    require_phone: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_website: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validate_phone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validate_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validate_website: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="searches")
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="search", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="search", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Search(id={self.id}, name='{self.name}', target={self.target_count})>"


class Company(Base):
    """Company lead record with extended fields."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("searches.id"), nullable=False, index=True
    )

    # Core fields (REQUIRED)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)  # NEW

    # Address fields
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Extended fields
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    keywords_matched: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)  # NEW: small, medium, large
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NEW

    # Scoring
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)  # NEW: 0-100

    # Validation status
    phone_validated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # NEW
    email_validated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # NEW
    website_validated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # NEW

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    search: Mapped["Search"] = relationship("Search", back_populates="companies")
    sources: Mapped[list["Source"]] = relationship(
        "Source", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.company_name}', quality={self.quality_score})>"


class Source(Base):
    """Source evidence for company data fields."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )

    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship("Company", back_populates="sources")

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, source='{self.source_name}', field='{self.field_name}')>"


class Run(Base):
    """Execution run tracking with progress."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("searches.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running", index=True
    )  # running, completed, failed, cancelled

    # Progress tracking (NEW)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_time_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds

    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    found_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discarded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    search: Mapped["Search"] = relationship("Search", back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, status='{self.status}', progress={self.progress_percent}%)>"


class APIKey(Base):
    """API Keys storage for external services."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    service_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    # google_places, bing_places, hunter_io, clearbit, etc.

    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    api_secret: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Additional config like rate limits, endpoints, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<APIKey(service='{self.service_name}', active={self.is_active})>"
