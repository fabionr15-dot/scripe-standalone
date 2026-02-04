"""Source Manager - Orchestrates multiple data sources for lead generation."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceResult, SourceType

logger = get_logger(__name__)


@dataclass
class SearchCriteria:
    """Search criteria for lead generation."""
    query: str  # Main search query (category, keywords)
    country: str = "IT"
    regions: list[str] | None = None
    cities: list[str] | None = None
    keywords_include: list[str] | None = None
    keywords_exclude: list[str] | None = None
    target_count: int = 100
    min_sources: int = 1  # Minimum sources to query
    max_sources: int | None = None  # None = all available


@dataclass
class SearchProgress:
    """Progress tracking for search operations."""
    total_sources: int
    completed_sources: int
    results_found: int
    target_count: int
    current_source: str | None = None
    errors: list[str] | None = None

    @property
    def percent_complete(self) -> int:
        """Get completion percentage."""
        if self.total_sources == 0:
            return 0
        return int((self.completed_sources / self.total_sources) * 100)

    @property
    def target_reached(self) -> bool:
        """Check if target count is reached."""
        return self.results_found >= self.target_count


class SourceManager:
    """Orchestrates multiple data sources for lead generation.

    Supports:
    - Parallel search across multiple sources
    - Cascade search (stop when target reached)
    - Priority-based source ordering
    - Country-specific source filtering
    - Health monitoring
    """

    def __init__(self):
        """Initialize source manager."""
        self._sources: dict[str, BaseConnector] = {}
        self.logger = get_logger(__name__)

    def register(self, source: BaseConnector) -> None:
        """Register a data source.

        Args:
            source: Source connector to register
        """
        self._sources[source.source_name] = source
        self.logger.info(
            "source_registered",
            source=source.source_name,
            type=source.config.source_type.value,
            priority=source.config.priority,
        )

    def unregister(self, source_name: str) -> None:
        """Unregister a data source.

        Args:
            source_name: Name of source to remove
        """
        if source_name in self._sources:
            del self._sources[source_name]
            self.logger.info("source_unregistered", source=source_name)

    def get_source(self, name: str) -> BaseConnector | None:
        """Get a specific source by name.

        Args:
            name: Source name

        Returns:
            Source connector or None
        """
        return self._sources.get(name)

    def list_sources(self) -> list[dict[str, Any]]:
        """List all registered sources with their status.

        Returns:
            List of source info dicts
        """
        return [
            {
                "name": source.source_name,
                "type": source.config.source_type.value,
                "priority": source.config.priority,
                "enabled": source.is_enabled,
                "countries": source.config.supported_countries,
                "requires_api_key": source.config.requires_api_key,
                "confidence_score": source.config.confidence_score,
            }
            for source in sorted(
                self._sources.values(),
                key=lambda s: s.config.priority
            )
        ]

    def get_sources_for_country(self, country: str) -> list[BaseConnector]:
        """Get sources that support a specific country.

        Args:
            country: Country code

        Returns:
            List of compatible sources, ordered by priority
        """
        compatible = [
            source for source in self._sources.values()
            if source.is_enabled and source.supports_country(country)
        ]
        return sorted(compatible, key=lambda s: s.config.priority)

    async def search_all(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[Callable] = None,
    ) -> list[SourceResult]:
        """Search all compatible sources in parallel.

        Args:
            criteria: Search criteria
            progress_callback: Optional callback for progress updates

        Returns:
            Combined results from all sources
        """
        sources = self.get_sources_for_country(criteria.country)

        if criteria.max_sources:
            sources = sources[:criteria.max_sources]

        if not sources:
            self.logger.warning("no_sources_available", country=criteria.country)
            return []

        progress = SearchProgress(
            total_sources=len(sources),
            completed_sources=0,
            results_found=0,
            target_count=criteria.target_count,
        )

        self.logger.info(
            "search_all_started",
            query=criteria.query,
            country=criteria.country,
            sources=[s.source_name for s in sources],
        )

        # Create tasks for parallel execution
        tasks = []
        for source in sources:
            task = self._search_source(source, criteria, progress, progress_callback)
            tasks.append(task)

        # Execute all in parallel
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_results: list[SourceResult] = []
        for i, results in enumerate(results_lists):
            if isinstance(results, Exception):
                self.logger.error(
                    "source_search_failed",
                    source=sources[i].source_name,
                    error=str(results),
                )
                continue
            if results:
                all_results.extend(results)

        self.logger.info(
            "search_all_completed",
            total_results=len(all_results),
            sources_queried=len(sources),
        )

        return all_results

    async def search_cascade(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[Callable] = None,
    ) -> list[SourceResult]:
        """Search sources in priority order, stopping when target reached.

        Args:
            criteria: Search criteria
            progress_callback: Optional callback for progress updates

        Returns:
            Results up to target count
        """
        sources = self.get_sources_for_country(criteria.country)

        if not sources:
            self.logger.warning("no_sources_available", country=criteria.country)
            return []

        progress = SearchProgress(
            total_sources=len(sources),
            completed_sources=0,
            results_found=0,
            target_count=criteria.target_count,
        )

        self.logger.info(
            "search_cascade_started",
            query=criteria.query,
            country=criteria.country,
            target=criteria.target_count,
            sources=[s.source_name for s in sources],
        )

        all_results: list[SourceResult] = []

        for source in sources:
            if progress.target_reached:
                self.logger.info(
                    "target_reached",
                    results=progress.results_found,
                    target=criteria.target_count,
                )
                break

            # How many more do we need?
            remaining = criteria.target_count - len(all_results)

            results = await self._search_source(
                source, criteria, progress, progress_callback, limit=remaining * 2
            )

            if results:
                all_results.extend(results)
                progress.results_found = len(all_results)

            progress.completed_sources += 1

            if progress_callback:
                progress_callback(progress)

        self.logger.info(
            "search_cascade_completed",
            total_results=len(all_results),
            sources_queried=progress.completed_sources,
        )

        return all_results[:criteria.target_count]

    async def _search_source(
        self,
        source: BaseConnector,
        criteria: SearchCriteria,
        progress: SearchProgress,
        progress_callback: Optional[Callable] = None,
        limit: int | None = None,
    ) -> list[SourceResult]:
        """Search a single source.

        Args:
            source: Source to search
            criteria: Search criteria
            progress: Progress tracker
            progress_callback: Optional callback
            limit: Override result limit

        Returns:
            Results from source
        """
        progress.current_source = source.source_name

        if progress_callback:
            progress_callback(progress)

        try:
            # Build region filter
            region = None
            if criteria.regions:
                region = criteria.regions[0]  # Use first region
            elif criteria.cities:
                region = criteria.cities[0]  # Use first city

            results = await source.search(
                query=criteria.query,
                region=region,
                limit=limit or source.config.max_results_per_query,
            )

            source.mark_healthy()
            return results

        except Exception as e:
            source.mark_unhealthy(str(e))
            source.log_error("search", e)
            if progress.errors is None:
                progress.errors = []
            progress.errors.append(f"{source.source_name}: {str(e)}")
            return []

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all sources.

        Returns:
            Dict of source_name -> is_healthy
        """
        results = {}
        for name, source in self._sources.items():
            try:
                results[name] = await source.health_check()
            except Exception:
                results[name] = False
        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get manager statistics.

        Returns:
            Statistics dict
        """
        sources = list(self._sources.values())
        return {
            "total_sources": len(sources),
            "enabled_sources": sum(1 for s in sources if s.is_enabled),
            "by_type": {
                t.value: sum(1 for s in sources if s.config.source_type == t)
                for t in SourceType
            },
            "sources": self.list_sources(),
        }


# Global instance
source_manager = SourceManager()


def get_source_manager() -> SourceManager:
    """Get the global source manager instance.

    Returns:
        SourceManager instance
    """
    return source_manager
