"""Setup and registration of all data sources."""

from app.infra.proxy_manager import get_proxy_manager
from app.logging_config import get_logger
from app.sources.bing_places import BingPlacesConnector
from app.sources.google_serp import GoogleSerpScraper
from app.sources.manager import get_source_manager
from app.sources.official_site import OfficialWebsiteCrawler
from app.sources.pagine_gialle import PagineGialleScraper
from app.sources.places import PlacesConnector

logger = get_logger(__name__)


def setup_sources(
    enable_scrapers: bool = True,
    proxy_list: list[str] | None = None,
) -> None:
    """Setup and register all data sources.

    Args:
        enable_scrapers: Whether to enable scraper-based sources
        proxy_list: Optional list of proxy URLs for scrapers
    """
    manager = get_source_manager()
    proxy_manager = get_proxy_manager()

    # Add proxies if provided
    if proxy_list:
        proxy_manager.add_proxies(proxy_list)

    # 1. Google Places API (highest priority)
    places = PlacesConnector()
    if places.api_key:
        manager.register(places)
        logger.info("registered_google_places")
    else:
        logger.warning("google_places_disabled_no_api_key")

    # 2. Bing Places API (second priority)
    bing = BingPlacesConnector()
    if bing.api_key:
        manager.register(bing)
        logger.info("registered_bing_places")
    else:
        logger.warning("bing_places_disabled_no_api_key")

    # 3. Google SERP Scraper (requires proxies)
    if enable_scrapers:
        serp = GoogleSerpScraper(proxy_manager=proxy_manager)
        manager.register(serp)
        logger.info("registered_google_serp")

    # 4. Pagine Gialle Scraper (Italy only, requires proxies)
    if enable_scrapers:
        pg = PagineGialleScraper(proxy_manager=proxy_manager)
        manager.register(pg)
        logger.info("registered_pagine_gialle")

    # 5. Official Website Crawler (for enrichment)
    website_crawler = OfficialWebsiteCrawler()
    manager.register(website_crawler)
    logger.info("registered_website_crawler")

    # Log summary
    stats = manager.get_statistics()
    logger.info(
        "sources_setup_complete",
        total_sources=stats["total_sources"],
        enabled_sources=stats["enabled_sources"],
    )


def get_sources_status() -> dict:
    """Get status of all registered sources.

    Returns:
        Dict with source statuses
    """
    manager = get_source_manager()
    return manager.get_statistics()


async def check_sources_health() -> dict[str, bool]:
    """Check health of all registered sources.

    Returns:
        Dict of source_name -> is_healthy
    """
    manager = get_source_manager()
    return await manager.health_check_all()
