"""Google Search SERP scraper for business discovery."""

import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from selectolax.parser import HTMLParser

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class GoogleSerpScraper(BaseConnector):
    """Google Search Results Page scraper for business discovery.

    Scrapes organic search results to find business websites.
    This requires proxy rotation to avoid being blocked.

    Note: This scraper is for educational/research purposes.
    Be mindful of Google's Terms of Service.
    """

    GOOGLE_SEARCH_URL = "https://www.google.com/search"

    # Source configuration
    config = SourceConfig(
        name="google_serp",
        source_type=SourceType.SCRAPER,
        priority=3,  # Third priority - use when APIs are exhausted
        rate_limit=0.5,  # Very slow - avoid detection
        requires_api_key=False,
        supported_countries=["*"],  # Can search any country
        enabled=True,
        confidence_score=0.6,  # Lower confidence - indirect source
        max_results_per_query=200,  # 10 per page, up to 20 pages
        timeout_seconds=120,  # Longer timeout for multiple pages
        retry_count=2,
        requires_proxy=True,  # Must use proxy to avoid blocks
    )

    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    def __init__(self, proxy_manager=None):
        """Initialize Google SERP scraper.

        Args:
            proxy_manager: Optional proxy manager for rotation
        """
        super().__init__()
        self.proxy_manager = proxy_manager
        self._user_agent_index = 0

    def _get_user_agent(self) -> str:
        """Get next user agent in rotation."""
        ua = self.USER_AGENTS[self._user_agent_index]
        self._user_agent_index = (self._user_agent_index + 1) % len(self.USER_AGENTS)
        return ua

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 30,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search Google for business-related queries.

        Args:
            query: Search query (e.g., "dentist", "restaurant")
            region: Geographic region to search in
            limit: Maximum results
            **kwargs: Additional parameters (country, language)

        Returns:
            List of source results (websites to crawl)
        """
        results = []

        # Build search query with location
        full_query = f"{query} {region}" if region else query

        # Add business-oriented search terms
        country = kwargs.get("country", "IT")
        language = kwargs.get("language", "it")

        try:
            # Calculate pages needed - allow up to 20 pages for large requests
            results_per_page = 10
            max_pages = 20  # Safety limit: max 200 results (20 * 10)
            pages_needed = min(max_pages, (limit + results_per_page - 1) // results_per_page)

            for page in range(pages_needed):
                if len(results) >= limit:
                    break

                page_results = await self._scrape_page(
                    query=full_query,
                    start=page * results_per_page,
                    country=country,
                    language=language,
                )

                if page_results:
                    results.extend(page_results)
                else:
                    # No results or blocked - stop
                    break

            self.log_search(full_query, len(results))

        except Exception as e:
            self.log_error("search", e)

        return results[:limit]

    async def _scrape_page(
        self,
        query: str,
        start: int = 0,
        country: str = "IT",
        language: str = "it",
    ) -> list[SourceResult]:
        """Scrape a single Google search results page.

        Args:
            query: Search query
            start: Result offset
            country: Country code for results
            language: Language code

        Returns:
            List of source results from this page
        """
        results = []

        # Build URL with parameters
        params = {
            "q": query,
            "start": start,
            "num": 10,
            "hl": language,
            "gl": country.lower(),
        }

        url = f"{self.GOOGLE_SEARCH_URL}?{urlencode(params)}"

        # Get proxy if available
        proxy = None
        if self.proxy_manager:
            proxy = await self.proxy_manager.get_proxy()

        try:
            headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": f"{language},{language.split('-')[0]};q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with httpx.AsyncClient(
                proxy=proxy,
                timeout=self.config.timeout_seconds,
            ) as client:
                response = await client.get(url, headers=headers)

                # Check for captcha or block
                if response.status_code == 429 or "captcha" in response.text.lower():
                    logger.warning("google_serp_blocked", proxy=proxy)
                    if self.proxy_manager and proxy:
                        await self.proxy_manager.report_blocked(proxy)
                    self.mark_unhealthy("Blocked by Google")
                    return []

                response.raise_for_status()

                # Parse results
                results = self._parse_serp(response.text, query)

                if results:
                    self.mark_healthy()

        except httpx.HTTPError as e:
            self.log_error("scrape_page", e)
            if self.proxy_manager and proxy:
                await self.proxy_manager.report_blocked(proxy)

        return results

    def _parse_serp(self, html: str, query: str) -> list[SourceResult]:
        """Parse Google SERP HTML to extract business websites.

        Args:
            html: HTML content
            query: Original search query

        Returns:
            List of source results
        """
        results = []
        parser = HTMLParser(html)

        # Find organic search results
        # Google's HTML structure changes frequently, so we use multiple selectors
        result_selectors = [
            "div.g",  # Classic result container
            "div[data-hveid]",  # Alternative container
        ]

        seen_domains = set()

        for selector in result_selectors:
            for result_div in parser.css(selector):
                try:
                    # Find the main link
                    link = result_div.css_first("a[href^='http']")
                    if not link:
                        continue

                    href = link.attributes.get("href", "")

                    # Skip Google's own links, ads, etc.
                    if self._should_skip_url(href):
                        continue

                    # Extract domain
                    parsed = urlparse(href)
                    domain = parsed.netloc.lower()

                    # Skip if we've already seen this domain
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    # Get title
                    title_elem = result_div.css_first("h3")
                    title = title_elem.text() if title_elem else domain

                    # Get snippet/description
                    snippet_elem = result_div.css_first("div[data-sncf]") or result_div.css_first("span.st")
                    snippet = snippet_elem.text() if snippet_elem else ""

                    # Create result - we mainly care about the website URL
                    # The official_website crawler will extract detailed info
                    result = SourceResult(
                        source_name=self.source_name,
                        company_name=self._extract_company_name(title, domain),
                        website=href,
                        source_url=f"https://www.google.com/search?q={query}",
                        raw_data={
                            "title": title,
                            "snippet": snippet,
                            "domain": domain,
                            "search_query": query,
                        },
                    )
                    results.append(result)

                except Exception as e:
                    logger.debug("serp_parse_error", error=str(e))
                    continue

        return results

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped.

        Args:
            url: URL to check

        Returns:
            True if should skip
        """
        skip_domains = [
            "google.com",
            "google.it",
            "gstatic.com",
            "googleapis.com",
            "youtube.com",
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "linkedin.com",
            "wikipedia.org",
            "amazon.com",
            "amazon.it",
            "tripadvisor.com",
            "tripadvisor.it",
            "yelp.com",
            "paginegialle.it",  # We have a dedicated scraper for this
        ]

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for skip in skip_domains:
            if skip in domain:
                return True

        # Skip tracking/redirect URLs
        if "/url?" in url or "googleadservices" in url:
            return True

        return False

    def _extract_company_name(self, title: str, domain: str) -> str:
        """Extract company name from title or domain.

        Args:
            title: Search result title
            domain: Website domain

        Returns:
            Best guess at company name
        """
        # Clean up title
        name = title

        # Remove common suffixes
        suffixes_to_remove = [
            " - Home",
            " | Home",
            " - Homepage",
            " | Homepage",
            " - Official Site",
            " | Official Site",
            " - Sito Ufficiale",
            " | Sito Ufficiale",
        ]
        for suffix in suffixes_to_remove:
            if name.endswith(suffix):
                name = name[: -len(suffix)]

        # If title is empty or just a domain, use cleaned domain
        if not name or name.lower() == domain:
            # Clean domain: "www.example.com" -> "Example"
            name = domain.replace("www.", "").split(".")[0].title()

        return name.strip()

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """SERP scraper doesn't support enrichment directly.

        Use official_website crawler for enrichment.
        """
        return None

    async def health_check(self) -> bool:
        """Check if Google is accessible (with current proxy).

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
                    "https://www.google.com",
                    headers={"User-Agent": self._get_user_agent()},
                )
                is_healthy = response.status_code == 200 and "captcha" not in response.text.lower()
                if is_healthy:
                    self.mark_healthy()
                else:
                    self.mark_unhealthy("Blocked or captcha")
                return is_healthy
        except Exception as e:
            self.mark_unhealthy(str(e))
            return False
