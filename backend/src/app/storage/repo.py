"""Repository layer for data access."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.storage.models import Company, Run, Search, Source

logger = get_logger(__name__)


class SearchRepository:
    """Repository for Search entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, criteria: dict[str, Any], target_count: int) -> Search:
        """Create a new search.

        Args:
            name: Search name
            criteria: Search criteria as dict
            target_count: Target number of companies

        Returns:
            Created search
        """
        search = Search(
            name=name,
            criteria_json=criteria,
            target_count=target_count,
        )
        self.session.add(search)
        self.session.flush()
        logger.info("search_created", search_id=search.id, name=name, target=target_count)
        return search

    def get_by_id(self, search_id: int) -> Search | None:
        """Get search by ID."""
        return self.session.get(Search, search_id)

    def list_all(self) -> list[Search]:
        """List all searches."""
        return list(self.session.scalars(select(Search).order_by(Search.created_at.desc())))


class CompanyRepository:
    """Repository for Company entities."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(
        self,
        search_id: int,
        company_name: str,
        website: str | None = None,
        phone: str | None = None,
        address_line: str | None = None,
        postal_code: str | None = None,
        city: str | None = None,
        region: str | None = None,
        country: str | None = None,
        category: str | None = None,
        keywords_matched: str | None = None,
        match_score: float = 0.0,
        confidence_score: float = 0.0,
    ) -> Company:
        """Upsert a company record.

        Args:
            search_id: Associated search ID
            company_name: Company name
            website: Website URL
            phone: Phone number
            address_line: Address
            postal_code: Postal code
            city: City
            region: Region
            country: Country
            category: Business category
            keywords_matched: Matched keywords (comma-separated)
            match_score: Match score (0-1)
            confidence_score: Confidence score (0-1)

        Returns:
            Company record
        """
        # Check for existing by normalized identifiers
        existing = None
        if website:
            existing = self.session.scalar(
                select(Company).where(
                    Company.search_id == search_id,
                    Company.website == website,
                )
            )

        if existing:
            # Update existing record
            existing.company_name = company_name
            existing.phone = phone or existing.phone
            existing.address_line = address_line or existing.address_line
            existing.postal_code = postal_code or existing.postal_code
            existing.city = city or existing.city
            existing.region = region or existing.region
            existing.country = country or existing.country
            existing.category = category or existing.category
            existing.keywords_matched = keywords_matched or existing.keywords_matched
            existing.match_score = max(match_score, existing.match_score)
            existing.confidence_score = max(confidence_score, existing.confidence_score)
            existing.updated_at = datetime.utcnow()
            logger.debug("company_updated", company_id=existing.id, name=company_name)
            return existing
        else:
            # Create new record
            company = Company(
                search_id=search_id,
                company_name=company_name,
                website=website,
                phone=phone,
                address_line=address_line,
                postal_code=postal_code,
                city=city,
                region=region,
                country=country,
                category=category,
                keywords_matched=keywords_matched,
                match_score=match_score,
                confidence_score=confidence_score,
            )
            self.session.add(company)
            self.session.flush()
            logger.debug("company_created", company_id=company.id, name=company_name)
            return company

    def count_by_search(self, search_id: int, min_quality: float = 0.0) -> int:
        """Count companies for a search that meet quality threshold."""
        stmt = select(Company).where(
            Company.search_id == search_id,
            Company.match_score >= min_quality,
        )
        return len(list(self.session.scalars(stmt)))

    def get_top_by_score(
        self, search_id: int, limit: int, min_match_score: float = 0.0
    ) -> list[Company]:
        """Get top companies by match score."""
        stmt = (
            select(Company)
            .where(
                Company.search_id == search_id,
                Company.match_score >= min_match_score,
            )
            .order_by(Company.match_score.desc(), Company.confidence_score.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))


class SourceRepository:
    """Repository for Source entities."""

    def __init__(self, session: Session):
        self.session = session

    def add_source(
        self,
        company_id: int,
        source_name: str,
        field_name: str,
        source_url: str | None = None,
        evidence_snippet: str | None = None,
    ) -> Source:
        """Add a source evidence record.

        Args:
            company_id: Associated company ID
            source_name: Source name (e.g., 'google_places', 'official_website')
            field_name: Field this source provides (e.g., 'phone', 'address')
            source_url: URL where data was found
            evidence_snippet: Snippet of evidence text

        Returns:
            Created source record
        """
        source = Source(
            company_id=company_id,
            source_name=source_name,
            source_url=source_url,
            field_name=field_name,
            evidence_snippet=evidence_snippet,
        )
        self.session.add(source)
        self.session.flush()
        return source


class RunRepository:
    """Repository for Run entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, search_id: int) -> Run:
        """Create a new run.

        Args:
            search_id: Associated search ID

        Returns:
            Created run
        """
        run = Run(search_id=search_id, status="running")
        self.session.add(run)
        self.session.flush()
        logger.info("run_created", run_id=run.id, search_id=search_id)
        return run

    def update_progress(
        self,
        run_id: int,
        progress_percent: int,
        current_step: str,
    ) -> Run:
        """Update run progress.

        Args:
            run_id: Run ID
            progress_percent: Progress percentage (0-100)
            current_step: Current step description

        Returns:
            Updated run
        """
        run = self.session.get(Run, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        run.progress_percent = progress_percent
        run.current_step = current_step

        logger.debug(
            "run_progress_updated",
            run_id=run_id,
            progress=progress_percent,
            step=current_step,
        )
        return run

    def update_status(
        self,
        run_id: int,
        status: str,
        found_count: int = 0,
        discarded_count: int = 0,
        notes: dict[str, Any] | None = None,
    ) -> Run:
        """Update run status.

        Args:
            run_id: Run ID
            status: New status
            found_count: Number of companies found
            discarded_count: Number discarded
            notes: Additional notes

        Returns:
            Updated run
        """
        run = self.session.get(Run, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        run.status = status
        run.found_count = found_count
        run.discarded_count = discarded_count
        if notes:
            run.notes_json = notes
        if status in ("completed", "failed", "cancelled"):
            run.ended_at = datetime.utcnow()

        logger.info(
            "run_updated",
            run_id=run_id,
            status=status,
            found=found_count,
            discarded=discarded_count,
        )
        return run

    def get_by_id(self, run_id: int) -> Run | None:
        """Get run by ID."""
        return self.session.get(Run, run_id)
