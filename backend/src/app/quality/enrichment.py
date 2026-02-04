"""Enrichment Pipeline - Enhances lead data from multiple sources."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.logging_config import get_logger
from app.quality.scorer import QualityScorer, QualityScore
from app.quality.tiers import QualityTier, TIER_CONFIG
from app.quality.validators import DataValidator, ValidationResult
from app.sources.base import SourceResult
from app.sources.manager import get_source_manager
from app.sources.official_site import OfficialWebsiteCrawler

logger = get_logger(__name__)


@dataclass
class EnrichmentResult:
    """Result of enrichment pipeline."""

    # Original data
    original: dict[str, Any]

    # Enriched data (merged from all sources)
    enriched: dict[str, Any]

    # Quality assessment
    quality_score: QualityScore

    # Validation results
    validations: dict[str, ValidationResult]

    # Source tracking
    sources_used: list[str] = field(default_factory=list)
    enrichment_sources: list[str] = field(default_factory=list)

    # Flags
    meets_tier: bool = False
    target_tier: QualityTier = QualityTier.STANDARD

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original": self.original,
            "enriched": self.enriched,
            "quality": self.quality_score.to_dict(),
            "validations": {
                k: {
                    "is_valid": v.is_valid,
                    "confidence": v.confidence,
                    "details": v.details,
                    "error": v.error,
                }
                for k, v in self.validations.items()
            },
            "sources_used": self.sources_used,
            "enrichment_sources": self.enrichment_sources,
            "meets_tier": self.meets_tier,
            "target_tier": self.target_tier.value,
        }


class EnrichmentPipeline:
    """Pipeline for enriching and validating lead data.

    Pipeline stages:
    1. Initial Data Collection (from search sources)
    2. Website Enrichment (crawl official site)
    3. Cross-Source Enrichment (query additional sources)
    4. Validation (phone, email, website)
    5. Quality Scoring
    6. Tier Assignment
    """

    def __init__(self):
        """Initialize enrichment pipeline."""
        self.logger = get_logger(__name__)
        self.scorer = QualityScorer()
        self.validator = DataValidator()
        self.website_crawler = OfficialWebsiteCrawler()

    async def enrich(
        self,
        data: dict[str, Any],
        target_tier: QualityTier = QualityTier.STANDARD,
        search_criteria: dict[str, Any] | None = None,
    ) -> EnrichmentResult:
        """Enrich lead data to meet target quality tier.

        Args:
            data: Initial lead data
            target_tier: Target quality tier
            search_criteria: Original search criteria for match scoring

        Returns:
            Enrichment result with enriched data and scores
        """
        tier_config = TIER_CONFIG[target_tier]
        enriched = data.copy()
        sources_used = [data.get("source", "unknown")]
        enrichment_sources = []

        self.logger.info(
            "enrichment_started",
            company=data.get("company_name"),
            target_tier=target_tier.value,
        )

        # Stage 1: Website Enrichment
        if tier_config.enrich_from_website and data.get("website"):
            website_data = await self._enrich_from_website(data)
            if website_data:
                enriched = self._merge_data(enriched, website_data)
                enrichment_sources.append("official_website")

        # Stage 2: Cross-Source Enrichment
        if len(sources_used) < tier_config.min_sources:
            additional_data = await self._enrich_from_sources(data, target_tier)
            for source_name, source_data in additional_data.items():
                enriched = self._merge_data(enriched, source_data)
                enrichment_sources.append(source_name)

        # Stage 3: Validation
        validation_level = self._get_validation_level(tier_config)
        validations = await self.validator.validate_all(enriched, validation_level)

        # Stage 4: Quality Scoring
        validation_results = {
            k: v.is_valid for k, v in validations.items()
        }
        quality_score = self.scorer.score(
            enriched,
            search_criteria=search_criteria,
            source_confidence=self._calc_source_confidence(sources_used + enrichment_sources),
            validation_results=validation_results,
        )

        # Stage 5: Check if meets tier
        meets_tier = quality_score.quality_score >= tier_config.min_score

        self.logger.info(
            "enrichment_completed",
            company=data.get("company_name"),
            quality_score=quality_score.quality_score,
            meets_tier=meets_tier,
            sources=len(sources_used) + len(enrichment_sources),
        )

        return EnrichmentResult(
            original=data,
            enriched=enriched,
            quality_score=quality_score,
            validations=validations,
            sources_used=sources_used,
            enrichment_sources=enrichment_sources,
            meets_tier=meets_tier,
            target_tier=target_tier,
        )

    async def enrich_batch(
        self,
        items: list[dict[str, Any]],
        target_tier: QualityTier = QualityTier.STANDARD,
        search_criteria: dict[str, Any] | None = None,
        max_concurrent: int = 5,
    ) -> list[EnrichmentResult]:
        """Enrich multiple leads concurrently.

        Args:
            items: List of lead data
            target_tier: Target quality tier
            search_criteria: Search criteria for match scoring
            max_concurrent: Maximum concurrent enrichments

        Returns:
            List of enrichment results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_limit(data: dict[str, Any]) -> EnrichmentResult:
            async with semaphore:
                return await self.enrich(data, target_tier, search_criteria)

        tasks = [enrich_with_limit(item) for item in items]
        return await asyncio.gather(*tasks)

    async def _enrich_from_website(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Enrich data by crawling company website.

        Args:
            data: Lead data with website

        Returns:
            Enriched data or None
        """
        website = data.get("website")
        if not website:
            return None

        try:
            result = await self.website_crawler.enrich({
                "website": website,
                "company_name": data.get("company_name"),
            })

            if result:
                return {
                    "phone": result.phone,
                    "email": getattr(result, "email", None),
                    "address_line": result.address_line,
                    "source": "official_website",
                }
        except Exception as e:
            self.logger.warning(
                "website_enrichment_failed",
                website=website,
                error=str(e),
            )

        return None

    async def _enrich_from_sources(
        self,
        data: dict[str, Any],
        target_tier: QualityTier,
    ) -> dict[str, dict[str, Any]]:
        """Enrich data from additional sources.

        Args:
            data: Lead data
            target_tier: Target tier

        Returns:
            Dict of source_name -> enriched data
        """
        manager = get_source_manager()
        tier_config = TIER_CONFIG[target_tier]
        results = {}

        # Get available sources
        sources = manager.get_sources_for_country(data.get("country", "IT"))

        # Filter to enrichment-capable sources
        enrichment_sources = [s for s in sources if hasattr(s, "enrich")]

        # Limit by tier config
        max_sources = tier_config.max_sources or len(enrichment_sources)
        enrichment_sources = enrichment_sources[:max_sources]

        # Try each source
        for source in enrichment_sources:
            try:
                result = await source.enrich(data)
                if result:
                    results[source.source_name] = {
                        "phone": result.phone,
                        "email": getattr(result, "email", None),
                        "website": result.website,
                        "address_line": result.address_line,
                        "city": result.city,
                        "region": result.region,
                    }
            except Exception as e:
                self.logger.debug(
                    "source_enrichment_failed",
                    source=source.source_name,
                    error=str(e),
                )

        return results

    def _merge_data(
        self,
        base: dict[str, Any],
        additional: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge additional data into base, preferring non-empty values.

        Args:
            base: Base data
            additional: Additional data to merge

        Returns:
            Merged data
        """
        result = base.copy()

        for key, value in additional.items():
            if value and not result.get(key):
                result[key] = value

        # Track that data was merged
        sources_count = result.get("sources_count", 1)
        result["sources_count"] = sources_count + 1
        result["enriched"] = True

        return result

    def _get_validation_level(self, tier_config) -> str:
        """Get validation level from tier config.

        Args:
            tier_config: Tier configuration

        Returns:
            Validation level string
        """
        if tier_config.validate_phone_carrier or tier_config.validate_email_smtp:
            return "premium"
        elif tier_config.validate_email_mx or tier_config.validate_website:
            return "standard"
        else:
            return "basic"

    def _calc_source_confidence(self, sources: list[str]) -> float:
        """Calculate confidence based on sources used.

        Args:
            sources: List of source names

        Returns:
            Confidence score
        """
        # More sources = higher confidence
        base_confidence = 0.5
        source_bonus = min(len(sources) * 0.15, 0.5)
        return base_confidence + source_bonus


class EnrichmentWorker:
    """Background worker for batch enrichment."""

    def __init__(self, pipeline: EnrichmentPipeline | None = None):
        """Initialize enrichment worker.

        Args:
            pipeline: Optional enrichment pipeline
        """
        self.pipeline = pipeline or EnrichmentPipeline()
        self.logger = get_logger(__name__)

    async def process_search_results(
        self,
        results: list[SourceResult],
        target_tier: QualityTier = QualityTier.STANDARD,
        search_criteria: dict[str, Any] | None = None,
        min_quality: float = 0.4,
        progress_callback: callable | None = None,
    ) -> list[EnrichmentResult]:
        """Process search results through enrichment pipeline.

        Args:
            results: Source results from search
            target_tier: Target quality tier
            search_criteria: Search criteria
            min_quality: Minimum quality score to keep
            progress_callback: Optional progress callback

        Returns:
            List of enriched results meeting quality threshold
        """
        total = len(results)
        enriched_results = []

        self.logger.info(
            "enrichment_batch_started",
            total=total,
            target_tier=target_tier.value,
        )

        # Convert SourceResult to dict
        items = [
            {
                "company_name": r.company_name,
                "website": r.website,
                "phone": r.phone,
                "email": getattr(r, "email", None),
                "address_line": r.address_line,
                "postal_code": r.postal_code,
                "city": r.city,
                "region": r.region,
                "country": r.country,
                "category": r.category,
                "source": r.source_name,
                "source_url": r.source_url,
            }
            for r in results
        ]

        # Process in batches
        batch_size = 10
        for i in range(0, total, batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self.pipeline.enrich_batch(
                batch,
                target_tier=target_tier,
                search_criteria=search_criteria,
            )

            # Filter by quality
            for result in batch_results:
                if result.quality_score.quality_score >= min_quality:
                    enriched_results.append(result)

            # Progress callback
            if progress_callback:
                progress_callback({
                    "processed": min(i + batch_size, total),
                    "total": total,
                    "enriched": len(enriched_results),
                    "percent": int((min(i + batch_size, total) / total) * 100),
                })

        self.logger.info(
            "enrichment_batch_completed",
            total=total,
            enriched=len(enriched_results),
            filtered=total - len(enriched_results),
        )

        return enriched_results
