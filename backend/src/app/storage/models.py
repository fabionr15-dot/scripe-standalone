"""Database models for lead storage."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Search(Base):
    """Search configuration and criteria."""

    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="search", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="search", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Search(id={self.id}, name='{self.name}', target={self.target_count})>"


class Company(Base):
    """Company lead record."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("searches.id"), nullable=False, index=True
    )

    # Core fields
    company_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Address fields
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Categorization
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    keywords_matched: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scoring
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

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
        return f"<Company(id={self.id}, name='{self.company_name}', match={self.match_score:.2f})>"


class Source(Base):
    """Source evidence for company data fields."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )

    # Source information
    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="sources")

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, source='{self.source_name}', field='{self.field_name}')>"


class Run(Base):
    """Execution run tracking."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("searches.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running", index=True
    )  # running, completed, failed, cancelled

    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    found_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discarded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    search: Mapped["Search"] = relationship("Search", back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, status='{self.status}', found={self.found_count})>"
