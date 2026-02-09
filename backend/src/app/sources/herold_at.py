"""Herold.at Austria scraper for business data."""

import re
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from selectolax.parser import HTMLParser

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class HeroldScraper(BaseConnector):
    """Herold.at Austria scraper for business data.

    Scrapes herold.at for Austrian business listings.
    The leading business directory for Austria.

    Note: Be respectful of rate limits and robots.txt.
    """

    BASE_URL = "https://www.herold.at"
    SEARCH_URL = "https://www.herold.at/gelbe-seiten/"

    # Source configuration
    config = SourceConfig(
        name="herold_at",
        source_type=SourceType.DIRECTORY,
        priority=4,  # After APIs
        rate_limit=1.0,  # Be respectful
        requires_api_key=False,
        supported_countries=["AT"],  # Austria only
        enabled=True,
        confidence_score=0.85,  # High confidence - authoritative Austrian source
        max_results_per_query=50,
        timeout_seconds=20,
        retry_count=2,
        requires_proxy=True,  # Use proxy to avoid blocks
    )

    # User agent for requests
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, proxy_manager=None):
        """Initialize Herold scraper.

        Args:
            proxy_manager: Optional proxy manager for rotation
        """
        super().__init__()
        self.proxy_manager = proxy_manager

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search Herold.at for businesses.

        Args:
            query: Search query (category, business type)
            region: Austrian city/region (e.g., "Wien", "Graz")
            limit: Maximum results
            **kwargs: Additional parameters

        Returns:
            List of source results
        """
        if not region:
            logger.warning("herold_search_requires_region")
            return []

        results = []

        try:
            # Calculate pages needed
            results_per_page = 20
            pages_needed = min(3, (limit + results_per_page - 1) // results_per_page)

            for page in range(1, pages_needed + 1):
                if len(results) >= limit:
                    break

                page_results = await self._scrape_page(
                    query=query,
                    region=region,
                    page=page,
                )

                if page_results:
                    results.extend(page_results)
                else:
                    # No results or blocked - stop
                    break

            self.log_search(f"{query} in {region}", len(results))

        except Exception as e:
            self.log_error("search", e)

        return results[:limit]

    async def _scrape_page(
        self,
        query: str,
        region: str,
        page: int = 1,
    ) -> list[SourceResult]:
        """Scrape a single page of Herold results.

        Args:
            query: Search query
            region: Region/city
            page: Page number (1-indexed)

        Returns:
            List of source results
        """
        results = []

        # Build URL using query parameters
        # Format: /gelbe-seiten/?what={query}&where={region}&page={page}
        encoded_query = quote_plus(query.lower())
        encoded_region = quote_plus(region)

        url = f"{self.SEARCH_URL}?what={encoded_query}&where={encoded_region}"
        if page > 1:
            url += f"&page={page}"

        # Get proxy if available
        proxy = None
        if self.proxy_manager:
            proxy = await self.proxy_manager.get_proxy()

        try:
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            }

            async with httpx.AsyncClient(
                proxy=proxy,
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)

                # Check for block
                if response.status_code == 403 or response.status_code == 429:
                    logger.warning("herold_blocked", proxy=proxy)
                    if self.proxy_manager and proxy:
                        await self.proxy_manager.report_blocked(proxy)
                    self.mark_unhealthy("Blocked by Herold")
                    return []

                response.raise_for_status()

                # Parse results
                results = self._parse_listing_page(response.text, query, region)

                if results:
                    self.mark_healthy()

        except httpx.HTTPError as e:
            self.log_error("scrape_page", e)
            if self.proxy_manager and proxy:
                await self.proxy_manager.report_blocked(proxy)

        return results

    def _parse_listing_page(self, html: str, query: str, region: str) -> list[SourceResult]:
        """Parse Herold listing page HTML.

        Args:
            html: HTML content
            query: Search query
            region: Search region

        Returns:
            List of source results
        """
        results = []
        parser = HTMLParser(html)

        # Find business listing cards
        # Herold uses various selectors for listings
        listing_selectors = [
            "article.result-item",
            "div.result-item",
            "[data-result-item]",
            ".search-result-item",
            "li.result",
        ]

        for selector in listing_selectors:
            listings = parser.css(selector)
            if listings:
                logger.debug(
                    "herold_found_listings",
                    selector=selector,
                    count=len(listings),
                )
                for listing in listings:
                    try:
                        result = self._parse_listing(listing, query, region)
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.debug("herold_parse_error", error=str(e))
                        continue
                break  # Found listings with this selector

        return results

    def _parse_listing(self, listing, query: str, region: str) -> SourceResult | None:
        """Parse a single business listing.

        Args:
            listing: Selectolax node for the listing
            query: Search query
            region: Search region

        Returns:
            Source result or None
        """
        # Company name
        name_elem = (
            listing.css_first("h2 a") or
            listing.css_first("h2") or
            listing.css_first(".company-name") or
            listing.css_first("[itemprop='name']")
        )
        if not name_elem:
            return None

        name = name_elem.text().strip()
        if not name:
            return None

        # Phone number
        phone = None
        phone_elem = (
            listing.css_first("a[href^='tel:']") or
            listing.css_first("[itemprop='telephone']") or
            listing.css_first(".phone")
        )
        if phone_elem:
            phone_href = phone_elem.attributes.get("href", "")
            if phone_href.startswith("tel:"):
                phone = phone_href.replace("tel:", "").strip()
            else:
                phone_text = phone_elem.text().strip()
                phone = re.sub(r"\s+", "", phone_text)

            # Add Austrian country code if not present
            if phone and not phone.startswith("+") and not phone.startswith("00"):
                phone = "+43" + phone.lstrip("0")

        # Website
        website = None
        website_elem = (
            listing.css_first("a[href*='website']") or
            listing.css_first("a.website-link") or
            listing.css_first("[itemprop='url']")
        )
        if website_elem:
            website = website_elem.attributes.get("href")
            if website and "herold.at" in website:
                website = None

        # Address
        address_line = None
        city = None
        postal_code = None

        address_elem = (
            listing.css_first("[itemprop='address']") or
            listing.css_first(".address") or
            listing.css_first("address")
        )
        if address_elem:
            address_text = address_elem.text()

            # Parse street
            street_match = re.search(r"^([^,\d]+\d*[a-zA-Z]?),", address_text)
            if street_match:
                address_line = street_match.group(1).strip()

            # Parse PLZ and city (4 digits for Austria)
            plz_city_match = re.search(r"(\d{4})\s+([A-Za-zäöüÄÖÜß\s-]+)", address_text)
            if plz_city_match:
                postal_code = plz_city_match.group(1)
                city = plz_city_match.group(2).strip()

        # Category
        category_elem = listing.css_first(".category, .branch")
        category = category_elem.text().strip() if category_elem else query

        # Source URL
        source_url = None
        detail_link = listing.css_first("a[href*='/gelbe-seiten/']") or name_elem
        if detail_link and hasattr(detail_link, "attributes"):
            href = detail_link.attributes.get("href")
            if href:
                source_url = urljoin(self.BASE_URL, href)

        return SourceResult(
            source_name=self.source_name,
            company_name=name,
            website=website,
            phone=phone,
            address_line=address_line,
            postal_code=postal_code,
            city=city or region,
            region=region,
            country="AT",
            category=category,
            source_url=source_url,
            raw_data={
                "search_query": query,
                "search_region": region,
            },
        )

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data by searching Herold.

        Args:
            company_data: Partial company data

        Returns:
            Enriched source result or None
        """
        name = company_data.get("company_name")
        city = company_data.get("city")

        if not name or not city:
            return None

        results = await self.search(name, region=city, limit=5)

        name_lower = name.lower()
        for result in results:
            if result.company_name.lower() == name_lower:
                return result

        if results:
            return results[0]

        return None

    async def health_check(self) -> bool:
        """Check if Herold.at is accessible."""
        try:
            proxy = None
            if self.proxy_manager:
                proxy = await self.proxy_manager.get_proxy()

            async with httpx.AsyncClient(
                proxy=proxy,
                timeout=10,
            ) as client:
                response = await client.get(
                    self.BASE_URL,
                    headers={"User-Agent": self.USER_AGENT},
                )
                is_healthy = response.status_code == 200
                if is_healthy:
                    self.mark_healthy()
                else:
                    self.mark_unhealthy(f"Status: {response.status_code}")
                return is_healthy
        except Exception as e:
            self.mark_unhealthy(str(e))
            return False
