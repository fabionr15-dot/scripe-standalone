"""Base classes for data source connectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


class SourceType(Enum):
    """Type of data source."""
    API = "api"           # Official API (Google Places, Bing Maps)
    SCRAPER = "scraper"   # Web scraping (Pagine Gialle, SERP)
    DIRECTORY = "directory"  # Business directories
    ENRICHMENT = "enrichment"  # Enrichment only (website crawler)


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    source_type: SourceType
    priority: int = 10  # Lower = higher priority (1-100)
    rate_limit: float = 1.0  # requests per second
    requires_api_key: bool = False
    api_key_env_var: str | None = None
    supported_countries: list[str] = field(default_factory=lambda: ["*"])  # "*" = all
    enabled: bool = True
    confidence_score: float = 0.7  # Base confidence for this source
    max_results_per_query: int = 100
    timeout_seconds: int = 30
    retry_count: int = 3
    requires_proxy: bool = False


class SourceResult:
    """Result from a data source."""

    def __init__(
        self,
        source_name: str,
        company_name: str,
        website: str | None = None,
        phone: str | None = None,
        address_line: str | None = None,
        postal_code: str | None = None,
        city: str | None = None,
        region: str | None = None,
        country: str | None = None,
        category: str | None = None,
        source_url: str | None = None,
        raw_data: dict[str, Any] | None = None,
    ):
        """Initialize source result.

        Args:
            source_name: Name of the source
            company_name: Company name
            website: Website URL
            phone: Phone number
            address_line: Address
            postal_code: Postal code
            city: City
            region: Region/state
            country: Country
            category: Business category
            source_url: URL where data was found
            raw_data: Raw data from source
        """
        self.source_name = source_name
        self.company_name = company_name
        self.website = website
        self.phone = phone
        self.address_line = address_line
        self.postal_code = postal_code
        self.city = city
        self.region = region
        self.country = country
        self.category = category
        self.source_url = source_url
        self.raw_data = raw_data or {}

    def __repr__(self) -> str:
        return f"<SourceResult(source={self.source_name}, company={self.company_name})>"


class BaseConnector(ABC):
    """Base class for data source connectors."""

    # Subclasses should override this
    config: SourceConfig = SourceConfig(
        name="base",
        source_type=SourceType.API,
        priority=50,
    )

    def __init__(self, source_name: str | None = None):
        """Initialize connector.

        Args:
            source_name: Unique source name (defaults to config.name)
        """
        self.source_name = source_name or self.config.name
        self.logger = get_logger(f"{__name__}.{self.source_name}")
        self._is_healthy = True
        self._last_error: str | None = None

    @property
    def priority(self) -> int:
        """Get source priority."""
        return self.config.priority

    @property
    def is_enabled(self) -> bool:
        """Check if source is enabled."""
        return self.config.enabled and self._is_healthy

    def supports_country(self, country: str) -> bool:
        """Check if source supports given country.

        Args:
            country: Country code (e.g., 'IT', 'DE')

        Returns:
            True if supported
        """
        if "*" in self.config.supported_countries:
            return True
        return country.upper() in [c.upper() for c in self.config.supported_countries]

    async def health_check(self) -> bool:
        """Check if source is healthy and available.

        Returns:
            True if healthy
        """
        # Default implementation - subclasses can override
        return self._is_healthy

    def mark_unhealthy(self, error: str) -> None:
        """Mark source as unhealthy.

        Args:
            error: Error description
        """
        self._is_healthy = False
        self._last_error = error
        self.logger.warning("source_unhealthy", source=self.source_name, error=error)

    def mark_healthy(self) -> None:
        """Mark source as healthy again."""
        self._is_healthy = True
        self._last_error = None

    @abstractmethod
    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search for companies.

        Args:
            query: Search query (keywords, category)
            region: Geographic region filter
            limit: Maximum results to return
            **kwargs: Additional source-specific parameters

        Returns:
            List of source results
        """
        pass

    @abstractmethod
    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich existing company data.

        Args:
            company_data: Partial company data to enrich

        Returns:
            Enriched source result or None
        """
        pass

    def log_search(self, query: str, result_count: int) -> None:
        """Log search operation.

        Args:
            query: Search query
            result_count: Number of results
        """
        self.logger.info(
            "source_search",
            source=self.source_name,
            query=query,
            results=result_count,
        )

    def log_error(self, operation: str, error: Exception) -> None:
        """Log error.

        Args:
            operation: Operation that failed
            error: Exception
        """
        self.logger.error(
            "source_error",
            source=self.source_name,
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
        )
