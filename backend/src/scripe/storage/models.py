"""Database models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from scripe.settings import settings


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Search(Base):
    """Search configuration."""

    __tablename__ = "searches"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    criteria_json = Column(JSON, nullable=False)
    target_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    companies = relationship("Company", back_populates="search", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="search", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Search(id={self.id}, name='{self.name}', target={self.target_count})>"


class Company(Base):
    """Company record."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=False)

    # Company data
    company_name = Column(String(500), nullable=False)
    website = Column(String(500))
    phone = Column(String(50))
    address_line = Column(Text)
    postal_code = Column(String(20))
    city = Column(String(200))
    region = Column(String(200))
    country = Column(String(100))
    category = Column(String(200))

    # Scoring
    match_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    search = relationship("Search", back_populates="companies")
    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.company_name}')>"


class Source(Base):
    """Source evidence for company data."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    source_name = Column(String(200), nullable=False)
    source_url = Column(Text)
    field_name = Column(String(100), nullable=False)
    evidence_snippet = Column(Text)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="sources")

    def __repr__(self) -> str:
        return f"<Source(company_id={self.company_id}, source='{self.source_name}')>"


class Run(Base):
    """Search execution run."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=False)

    status = Column(String(50), nullable=False, default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    found_count = Column(Integer, default=0)
    discarded_count = Column(Integer, default=0)
    notes_json = Column(JSON)

    # Relationships
    search = relationship("Search", back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, search_id={self.search_id}, status='{self.status}')>"


# Database engine and session
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
