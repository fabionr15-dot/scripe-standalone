"""Main pipeline runner for lead generation."""

import asyncio
from datetime import datetime
from typing import Any

from app.dedupe.deduper import CompanyDeduplicator
from app.extractors.normalizers import (
    AddressNormalizer,
    CompanyNameNormalizer,
    WebsiteNormalizer,
)
from app.extractors.phone import PhoneExtractor
from app.logging_config import get_logger
from app.matcher.scoring import CompanyScorer
from app.sources.base import BaseConnector, SourceResult
from app.sources.official_site import OfficialWebsiteCrawler
from app.sources.places import PlacesConnector
from app.storage.db import Database
from app.storage.repo import CompanyRepository, RunRepository, SearchRepository, SourceRepository

logger = get_logger(__name__)


class PipelineRunner:
    """Orchestrates the lead generation pipeline."""

    def __init__(self, database: Database):
        """Initialize pipeline runner.

        Args:
            database: Database instance
        """
        self.db = database
        self.phone_extractor = PhoneExtractor()
        self.deduplicator = CompanyDeduplicator()

        # Normalizers
        self.website_normalizer = WebsiteNormalizer()
        self.address_normalizer = AddressNormalizer()
        self.name_normalizer = CompanyNameNormalizer()

        # Source connectors
        self.connectors: dict[str, BaseConnector] = {
            "google_places": PlacesConnector(),
            "official_website": OfficialWebsiteCrawler(),
        }

    async def run_search(self, search_id: int) -> dict[str, Any]:
        """Execute a search pipeline.

        Args:
            search_id: Search ID to execute

        Returns:
            Run statistics
        """
        logger.info("pipeline_started", search_id=search_id)

        with self.db.session() as session:
            search_repo = SearchRepository(session)
            run_repo = RunRepository(session)
            company_repo = CompanyRepository(session)

            # Get search
            search = search_repo.get_by_id(search_id)
            if not search:
                raise ValueError(f"Search {search_id} not found")

            # Create run
            run = run_repo.create(search_id)
            session.commit()

            try:
                # Initialize scorer
                scorer = CompanyScorer(search.criteria_json)

                # Step 1: Collect raw results from sources (0-30%)
                run_repo.update_progress(run.id, 5, "Collecting leads from sources...")
                session.commit()
                logger.info("step_collect_starting", target_count=search.target_count)
                raw_results = await self._collect_from_sources(
                    search.criteria_json, search.target_count
                )
                logger.info("step_collect_completed", raw_count=len(raw_results))
                run_repo.update_progress(run.id, 30, f"Collected {len(raw_results)} raw results")
                session.commit()

                # Step 2: Normalize and validate (30-45%)
                run_repo.update_progress(run.id, 35, "Normalizing and validating data...")
                session.commit()
                logger.info("step_normalize_starting")
                normalized_results = self._normalize_results(raw_results)
                logger.info("step_normalize_completed", normalized_count=len(normalized_results))
                run_repo.update_progress(run.id, 45, f"Normalized {len(normalized_results)} results")
                session.commit()

                # Step 3: Enrich missing data (45-60%)
                run_repo.update_progress(run.id, 50, "Enriching data (emails, phones)...")
                session.commit()
                logger.info("step_enrich_starting")
                enriched_results = await self._enrich_results(normalized_results)
                logger.info("step_enrich_completed", enriched_count=len(enriched_results))
                run_repo.update_progress(run.id, 60, f"Enriched {len(enriched_results)} results")
                session.commit()

                # Step 4: Deduplicate (60-70%)
                run_repo.update_progress(run.id, 65, "Removing duplicates...")
                session.commit()
                logger.info("step_dedupe_starting")
                deduplicated_results = self.deduplicator.deduplicate_batch(enriched_results)
                logger.info("step_dedupe_completed", dedupe_count=len(deduplicated_results))
                run_repo.update_progress(run.id, 70, f"Removed duplicates, {len(deduplicated_results)} unique")
                session.commit()

                # Step 5: Score and filter (70-85%)
                run_repo.update_progress(run.id, 75, "Calculating quality scores...")
                session.commit()
                logger.info("step_score_starting")
                scored_results = self._score_results(deduplicated_results, scorer)
                filtered_results = self._filter_by_quality(scored_results, scorer)
                logger.info(
                    "step_score_completed",
                    scored_count=len(scored_results),
                    filtered_count=len(filtered_results),
                )
                run_repo.update_progress(run.id, 85, f"Filtered to {len(filtered_results)} high-quality leads")
                session.commit()

                # Step 6: Save to database (85-100%)
                run_repo.update_progress(run.id, 90, "Saving results to database...")
                session.commit()
                logger.info("step_save_starting")
                saved_count = self._save_results(
                    session, search_id, filtered_results, search.target_count
                )
                logger.info("step_save_completed", saved_count=saved_count)
                run_repo.update_progress(run.id, 100, f"Completed! Saved {saved_count} leads")
                session.commit()

                # Update run status
                discarded_count = len(scored_results) - saved_count
                run_repo.update_status(
                    run.id,
                    status="completed",
                    found_count=saved_count,
                    discarded_count=discarded_count,
                    notes={
                        "raw_results": len(raw_results),
                        "after_normalization": len(normalized_results),
                        "after_enrichment": len(enriched_results),
                        "after_deduplication": len(deduplicated_results),
                        "after_scoring": len(scored_results),
                        "after_filtering": len(filtered_results),
                    },
                )
                session.commit()

                logger.info(
                    "pipeline_completed",
                    search_id=search_id,
                    run_id=run.id,
                    found=saved_count,
                    discarded=discarded_count,
                )

                return {
                    "run_id": run.id,
                    "status": "completed",
                    "found_count": saved_count,
                    "discarded_count": discarded_count,
                    "target_count": search.target_count,
                }

            except Exception as e:
                logger.error("pipeline_failed", search_id=search_id, error=str(e))
                run_repo.update_status(run.id, status="failed", notes={"error": str(e)})
                session.commit()
                raise

    async def _collect_from_sources(
        self, criteria: dict[str, Any], target_count: int
    ) -> list[SourceResult]:
        """Collect results from all enabled sources.

        Args:
            criteria: Search criteria
            target_count: Target number of results

        Returns:
            List of raw source results
        """
        results = []

        # Build queries based on criteria
        keywords = criteria.get("keywords_include", [])
        categories = criteria.get("categories", [])
        regions = criteria.get("regions", [])

        # Generate search queries
        queries = []
        for category in categories:
            for region in regions:
                queries.append({"query": category, "region": region})

        # If no categories, use keywords
        if not queries:
            for keyword in keywords:
                for region in regions:
                    queries.append({"query": keyword, "region": region})

        # Limit queries to avoid excessive API calls
        queries = queries[: min(10, len(queries))]

        # Execute searches (could parallelize further)
        for query_params in queries:
            if len(results) >= target_count * 2:  # Collect 2x target for filtering
                break

            # Try Places first
            places_connector = self.connectors.get("google_places")
            if places_connector:
                try:
                    places_results = await places_connector.search(
                        query=query_params["query"],
                        region=query_params["region"],
                        limit=min(50, target_count),
                    )
                    results.extend(places_results)
                    logger.info(
                        "source_collected",
                        source="google_places",
                        query=query_params["query"],
                        count=len(places_results),
                    )
                except Exception as e:
                    logger.error("source_error", source="google_places", error=str(e))

        return results

    def _normalize_results(self, results: list[SourceResult]) -> list[dict[str, Any]]:
        """Normalize and clean source results.

        Args:
            results: Raw source results

        Returns:
            Normalized company dicts
        """
        normalized = []

        for result in results:
            # Normalize fields
            company_name = self.name_normalizer.normalize(result.company_name)
            website = self.website_normalizer.normalize(result.website) if result.website else None
            phone = (
                self.phone_extractor.normalize(result.phone, result.country)
                if result.phone
                else None
            )
            city = self.address_normalizer.normalize_city(result.city) if result.city else None
            region = (
                self.address_normalizer.normalize_region(result.region)
                if result.region
                else None
            )
            postal_code = (
                self.address_normalizer.normalize_postal_code(result.postal_code, result.country)
                if result.postal_code
                else None
            )

            normalized.append(
                {
                    "source_name": result.source_name,
                    "company_name": company_name,
                    "website": website,
                    "phone": phone,
                    "address_line": result.address_line,
                    "postal_code": postal_code,
                    "city": city,
                    "region": region,
                    "country": result.country,
                    "category": result.category,
                    "source_url": result.source_url,
                    "raw_data": result.raw_data,
                }
            )

        return normalized

    async def _enrich_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich results with missing data.

        Args:
            results: Normalized results

        Returns:
            Enriched results
        """
        enriched = []
        website_crawler = self.connectors.get("official_website")

        for result in results:
            # If missing phone and has website, try to enrich from website
            if not result.get("phone") and result.get("website") and website_crawler:
                try:
                    enrichment = await website_crawler.enrich(result)
                    if enrichment and enrichment.phone:
                        result["phone"] = self.phone_extractor.normalize(
                            enrichment.phone, result.get("country")
                        )
                        logger.debug(
                            "enriched_from_website",
                            company=result.get("company_name"),
                            found_phone=bool(result["phone"]),
                        )
                except Exception as e:
                    logger.debug("enrichment_error", company=result.get("company_name"), error=str(e))

            enriched.append(result)

        return enriched

    def _score_results(
        self, results: list[dict[str, Any]], scorer: CompanyScorer
    ) -> list[dict[str, Any]]:
        """Calculate match and confidence scores.

        Args:
            results: Results to score
            scorer: Company scorer

        Returns:
            Scored results
        """
        for result in results:
            match_score = scorer.calculate_match_score(
                company_name=result.get("company_name", ""),
                category=result.get("category"),
                region=result.get("region"),
                city=result.get("city"),
                website=result.get("website"),
            )

            confidence_score = scorer.calculate_confidence_score(
                source_name=result.get("source_name", ""),
                has_phone=bool(result.get("phone")),
                has_website=bool(result.get("website")),
                has_address=bool(result.get("address_line")),
                phone_source=result.get("source_name") if result.get("phone") else None,
            )

            result["match_score"] = match_score
            result["confidence_score"] = confidence_score

        return results

    def _filter_by_quality(
        self, results: list[dict[str, Any]], scorer: CompanyScorer
    ) -> list[dict[str, Any]]:
        """Filter results by quality requirements.

        Args:
            results: Scored results
            scorer: Company scorer

        Returns:
            Filtered results
        """
        filtered = []

        for result in results:
            if scorer.passes_quality_requirements(
                match_score=result.get("match_score", 0.0),
                confidence_score=result.get("confidence_score", 0.0),
                has_phone=bool(result.get("phone")),
                has_website=bool(result.get("website")),
            ):
                filtered.append(result)

        return filtered

    def _save_results(
        self,
        session: Any,
        search_id: int,
        results: list[dict[str, Any]],
        target_count: int,
    ) -> int:
        """Save results to database.

        Args:
            session: Database session
            search_id: Search ID
            results: Results to save
            target_count: Target count (take top N)

        Returns:
            Number saved
        """
        company_repo = CompanyRepository(session)
        source_repo = SourceRepository(session)

        # Sort by score and take top N
        sorted_results = sorted(
            results,
            key=lambda r: (r.get("match_score", 0.0), r.get("confidence_score", 0.0)),
            reverse=True,
        )[:target_count]

        saved_count = 0

        for result in sorted_results:
            # Upsert company
            company = company_repo.upsert(
                search_id=search_id,
                company_name=result.get("company_name", ""),
                website=result.get("website"),
                phone=result.get("phone"),
                address_line=result.get("address_line"),
                postal_code=result.get("postal_code"),
                city=result.get("city"),
                region=result.get("region"),
                country=result.get("country"),
                category=result.get("category"),
                match_score=result.get("match_score", 0.0),
                confidence_score=result.get("confidence_score", 0.0),
            )

            # Add source evidence
            if result.get("source_url"):
                for field_name in ["phone", "website", "address_line"]:
                    if result.get(field_name):
                        source_repo.add_source(
                            company_id=company.id,
                            source_name=result.get("source_name", ""),
                            field_name=field_name,
                            source_url=result.get("source_url"),
                        )

            saved_count += 1

        return saved_count
