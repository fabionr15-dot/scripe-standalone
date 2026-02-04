"""Repository layer for database operations."""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from scripe.logging_config import get_logger
from scripe.storage.models import Company, Run, Search, Source

logger = get_logger(__name__)


class SearchRepository:
    """Repository for Search operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, criteria: dict[str, Any], target_count: int) -> Search:
        """Create a new search."""
        search = Search(
            name=name,
            criteria_json=criteria,
            target_count=target_count,
        )
        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)
        logger.info("search_created", search_id=search.id, name=name)
        return search

    def get_by_id(self, search_id: int) -> Search | None:
        """Get search by ID."""
        return self.db.query(Search).filter(Search.id == search_id).first()

    def get_by_name(self, name: str) -> Search | None:
        """Get search by name."""
        return self.db.query(Search).filter(Search.name == name).first()

    def list_all(self) -> list[Search]:
        """List all searches."""
        return self.db.query(Search).order_by(Search.created_at.desc()).all()


class CompanyRepository:
    """Repository for Company operations."""

    def __init__(self, db: Session):
        self.db = db

    def upsert(
        self,
        search_id: int,
        company_data: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> Company:
        """Insert or update company with sources."""
        # Check for existing company by website or phone
        existing = None
        if company_data.get("website"):
            existing = (
                self.db.query(Company)
                .filter(
                    Company.search_id == search_id,
                    Company.website == company_data["website"],
                )
                .first()
            )

        if not existing and company_data.get("phone"):
            existing = (
                self.db.query(Company)
                .filter(
                    Company.search_id == search_id,
                    Company.phone == company_data["phone"],
                )
                .first()
            )

        if existing:
            # Update existing
            for key, value in company_data.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            company = existing
        else:
            # Create new
            company = Company(search_id=search_id, **company_data)
            self.db.add(company)
            self.db.flush()

        # Add sources
        for source_data in sources:
            source = Source(company_id=company.id, **source_data)
            self.db.add(source)

        self.db.commit()
        self.db.refresh(company)
        return company

    def count_valid(self, search_id: int, min_score: float = 0.0) -> int:
        """Count valid companies for search."""
        return (
            self.db.query(func.count(Company.id))
            .filter(
                Company.search_id == search_id,
                Company.match_score >= min_score,
            )
            .scalar()
        )

    def get_top_companies(
        self,
        search_id: int,
        limit: int,
        min_score: float = 0.0,
    ) -> list[Company]:
        """Get top companies by score."""
        return (
            self.db.query(Company)
            .filter(
                Company.search_id == search_id,
                Company.match_score >= min_score,
            )
            .order_by(Company.match_score.desc(), Company.confidence_score.desc())
            .limit(limit)
            .all()
        )

    def get_all_for_search(self, search_id: int) -> list[Company]:
        """Get all companies for a search."""
        return (
            self.db.query(Company)
            .filter(Company.search_id == search_id)
            .order_by(Company.match_score.desc())
            .all()
        )


class RunRepository:
    """Repository for Run operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, search_id: int) -> Run:
        """Create a new run."""
        run = Run(search_id=search_id, status="running")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info("run_created", run_id=run.id, search_id=search_id)
        return run

    def update_status(
        self,
        run_id: int,
        status: str,
        found_count: int | None = None,
        discarded_count: int | None = None,
        notes: dict[str, Any] | None = None,
    ) -> Run:
        """Update run status."""
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        run.status = status
        if found_count is not None:
            run.found_count = found_count
        if discarded_count is not None:
            run.discarded_count = discarded_count
        if notes is not None:
            run.notes_json = notes

        if status in ("completed", "failed"):
            run.ended_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_id(self, run_id: int) -> Run | None:
        """Get run by ID."""
        return self.db.query(Run).filter(Run.id == run_id).first()
