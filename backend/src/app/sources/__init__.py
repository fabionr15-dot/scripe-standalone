"""Data source connectors for lead generation."""

from app.sources.base import (
    BaseConnector,
    SourceConfig,
    SourceResult,
    SourceType,
)
from app.sources.bing_places import BingPlacesConnector
from app.sources.google_serp import GoogleSerpScraper
from app.sources.manager import (
    SearchCriteria,
    SearchProgress,
    SourceManager,
    get_source_manager,
    source_manager,
)
from app.sources.official_site import OfficialWebsiteCrawler
from app.sources.pagine_gialle import PagineGialleScraper
from app.sources.places import PlacesConnector

__all__ = [
    # Base
    "BaseConnector",
    "SourceConfig",
    "SourceResult",
    "SourceType",
    # Manager
    "SourceManager",
    "source_manager",
    "get_source_manager",
    "SearchCriteria",
    "SearchProgress",
    # Connectors
    "PlacesConnector",
    "BingPlacesConnector",
    "GoogleSerpScraper",
    "PagineGialleScraper",
    "OfficialWebsiteCrawler",
]
