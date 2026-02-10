"""Pagine Gialle Italia scraper for business data."""

import re
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from selectolax.parser import HTMLParser

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class PagineGialleScraper(BaseConnector):
    """Pagine Gialle Italia scraper for business data.

    Scrapes paginegialle.it for Italian business listings.
    Very rich data source for Italy.

    Note: Be respectful of rate limits and robots.txt.
    """

    BASE_URL = "https://www.paginegialle.it"
    SEARCH_URL = "https://www.paginegialle.it/ricerca"

    # Source configuration
    config = SourceConfig(
        name="pagine_gialle",
        source_type=SourceType.DIRECTORY,
        priority=4,  # After APIs and SERP
        rate_limit=1.0,  # Be respectful
        requires_api_key=False,
        supported_countries=["IT"],  # Italy only
        enabled=True,
        confidence_score=0.8,  # Good confidence - authoritative Italian source
        max_results_per_query=500,  # 25 per page, up to 20 pages
        timeout_seconds=120,  # Longer timeout for multiple pages
        retry_count=2,
        requires_proxy=True,  # Use proxy to avoid blocks
    )

    # User agent for requests
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, proxy_manager=None):
        """Initialize Pagine Gialle scraper.

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
        """Search Pagine Gialle for businesses.

        Args:
            query: Search query (category, business type)
            region: Italian region/city (e.g., "Milano", "Roma")
            limit: Maximum results
            **kwargs: Additional parameters

        Returns:
            List of source results
        """
        if not region:
            logger.warning("paginegialle_search_requires_region")
            return []

        results = []

        try:
            # Calculate pages needed - allow up to 20 pages for large requests
            results_per_page = 25
            max_pages = 20  # Safety limit: max 500 results (20 * 25)
            pages_needed = min(max_pages, (limit + results_per_page - 1) // results_per_page)

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
        """Scrape a single page of Pagine Gialle results.

        Args:
            query: Search query
            region: Region/city
            page: Page number (1-indexed)

        Returns:
            List of source results
        """
        results = []

        # Build URL
        # Format: /ricerca/{query}/{region}/p-{page}
        encoded_query = quote_plus(query.lower())
        encoded_region = quote_plus(region.lower())

        if page == 1:
            url = f"{self.SEARCH_URL}/{encoded_query}/{encoded_region}"
        else:
            url = f"{self.SEARCH_URL}/{encoded_query}/{encoded_region}/p-{page}"

        # Get proxy if available
        proxy = None
        if self.proxy_manager:
            proxy = await self.proxy_manager.get_proxy()

        try:
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
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
                    logger.warning("paginegialle_blocked", proxy=proxy)
                    if self.proxy_manager and proxy:
                        await self.proxy_manager.report_blocked(proxy)
                    self.mark_unhealthy("Blocked by Pagine Gialle")
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
        """Parse Pagine Gialle listing page HTML.

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
        # Pagine Gialle 2024/2025 redesign uses .search-itm class
        listing_selectors = [
            "div.search-itm",  # New 2024+ main listing container
            "article.search-itm",  # Alternative
            "div.vcard",  # Legacy listing container
            "article.listing-item",  # Legacy alternative
            "div[itemtype='http://schema.org/LocalBusiness']",  # Schema.org markup
        ]

        for selector in listing_selectors:
            listings = parser.css(selector)
            if listings:
                logger.debug(
                    "paginegialle_found_listings",
                    selector=selector,
                    count=len(listings),
                )
                for listing in listings:
                    try:
                        result = self._parse_listing(listing, query, region)
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.debug("paginegialle_parse_error", error=str(e))
                        continue
                break  # Found listings with this selector, don't try others

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
        # Company name - try new selectors first, then legacy
        name_elem = (
            listing.css_first("h2.search-itm__rag") or  # New 2024+ selector
            listing.css_first(".search-itm__rag") or  # Alternative new
            listing.css_first("h2.org") or  # Legacy
            listing.css_first("span.fn") or
            listing.css_first("[itemprop='name']") or
            listing.css_first("a.listing-name")
        )
        if not name_elem:
            return None

        name = name_elem.text().strip()
        if not name:
            return None

        # Phone number - try new selectors first
        phone = None
        phone_elem = (
            listing.css_first(".search-itm__phone") or  # New 2024+ selector
            listing.css_first("span.tel") or  # Legacy
            listing.css_first("[itemprop='telephone']") or
            listing.css_first("a[href^='tel:']")
        )
        if phone_elem:
            phone_text = phone_elem.text().strip()
            # Clean phone - extract first valid number
            phone_numbers = re.findall(r"[\d\s]+", phone_text)
            if phone_numbers:
                # Take first phone number, clean it
                phone = re.sub(r"\s+", "", phone_numbers[0])
                if phone and len(phone) >= 6:  # Valid phone length
                    # Add Italian country code if not present
                    if not phone.startswith("+") and not phone.startswith("00"):
                        phone = "+39" + phone

        # Website - look for external links
        website = None
        website_elem = (
            listing.css_first("a[data-shinystat-name='sito']") or  # New tracking attr
            listing.css_first("a.search-itm__sito") or  # New class
            listing.css_first("a.url") or  # Legacy
            listing.css_first("[itemprop='url']")
        )
        if website_elem:
            website = website_elem.attributes.get("href")
            # Skip if it's a Pagine Gialle internal link or WhatsApp
            if website and ("paginegialle.it" in website or "wa.me" in website):
                website = None

        # Address - parse from new format
        address_line = None
        city = None
        postal_code = None
        region_name = None

        address_elem = (
            listing.css_first(".search-itm__adr") or  # New 2024+ selector
            listing.css_first("div.street-address") or  # Legacy
            listing.css_first("[itemprop='streetAddress']")
        )
        if address_elem:
            # New format: "Lombardia\nVia xyz, 2-\n20121\nMilano (MI)"
            address_text = address_elem.text()
            address_lines = [line.strip() for line in address_text.split("\n") if line.strip()]

            if address_lines:
                # First line is often the region
                if len(address_lines) >= 1 and address_lines[0] in [
                    "Lombardia", "Lazio", "Campania", "Piemonte", "Veneto",
                    "Emilia-Romagna", "Toscana", "Sicilia", "Puglia", "Liguria",
                    "Marche", "Calabria", "Sardegna", "Friuli-Venezia Giulia",
                    "Abruzzo", "Trentino-Alto Adige", "Umbria", "Basilicata",
                    "Molise", "Valle d'Aosta"
                ]:
                    region_name = address_lines[0]
                    address_lines = address_lines[1:]

                # Find street address (contains "Via", "Piazza", etc.)
                for line in address_lines:
                    if any(kw in line.lower() for kw in ["via", "piazza", "corso", "viale", "largo", "vicolo"]):
                        address_line = line.rstrip("-").strip()
                        break

                # Find postal code (5 digits)
                for line in address_lines:
                    postal_match = re.search(r"\b(\d{5})\b", line)
                    if postal_match:
                        postal_code = postal_match.group(1)
                        break

                # Find city (usually last line with province in parentheses)
                for line in address_lines:
                    city_match = re.search(r"([A-Za-zÀ-ú\s]+)\s*\([A-Z]{2}\)", line)
                    if city_match:
                        city = city_match.group(1).strip()
                        break

        # Category
        category_elem = (
            listing.css_first(".search-itm__category") or  # New 2024+
            listing.css_first("span.category")  # Legacy
        )
        category = category_elem.text().strip() if category_elem else query

        # Source URL (detail page link)
        source_url = None
        detail_link = (
            listing.css_first("a.search-itm__rag") or  # New: name is link
            listing.css_first("h2.search-itm__rag a") or
            name_elem
        )
        if detail_link:
            href = detail_link.attributes.get("href") if hasattr(detail_link, "attributes") else None
            if not href and name_elem.parent:
                href = name_elem.parent.attributes.get("href") if hasattr(name_elem.parent, "attributes") else None
            if href and not href.startswith("http"):
                source_url = urljoin(self.BASE_URL, href)
            elif href:
                source_url = href

        return SourceResult(
            source_name=self.source_name,
            company_name=name,
            website=website,
            phone=phone,
            address_line=address_line,
            postal_code=postal_code,
            city=city or region,
            region=region_name or region,
            country="IT",
            category=category,
            source_url=source_url,
            raw_data={
                "search_query": query,
                "search_region": region,
            },
        )

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data by searching Pagine Gialle.

        Args:
            company_data: Partial company data (should include name and city)

        Returns:
            Enriched source result or None
        """
        name = company_data.get("company_name")
        city = company_data.get("city")

        if not name or not city:
            return None

        # Search for the specific business
        results = await self.search(name, region=city, limit=5)

        # Try to find an exact match
        name_lower = name.lower()
        for result in results:
            if result.company_name.lower() == name_lower:
                return result

        # Return first result if close enough
        if results:
            return results[0]

        return None

    async def health_check(self) -> bool:
        """Check if Pagine Gialle is accessible.

        Returns:
            True if accessible
        """
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
