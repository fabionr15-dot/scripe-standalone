"""Official website crawler for contact information."""

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from app.extractors.normalizers import TextCleaner, WebsiteNormalizer
from app.extractors.phone import PhoneExtractor
from app.logging_config import get_logger
from app.settings import settings
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class OfficialWebsiteCrawler(BaseConnector):
    """Crawl official company websites for contact information.

    Respects robots.txt and crawls only public contact pages.
    This is an enrichment-only source - it does not search for new companies.
    """

    CONTACT_URL_PATTERNS = [
        "/contact",
        "/contatti",
        "/contact-us",
        "/chi-siamo",
        "/about",
        "/about-us",
        "/impressum",
        "/legal",
        "/kontakt",
    ]

    # Source configuration
    config = SourceConfig(
        name="official_website",
        source_type=SourceType.ENRICHMENT,
        priority=100,  # Used for enrichment after search
        rate_limit=2.0,  # Be respectful to websites
        requires_api_key=False,
        supported_countries=["*"],  # Global - any website
        enabled=True,
        confidence_score=0.95,  # High confidence - direct source
        max_results_per_query=1,  # One company at a time
        timeout_seconds=15,
        retry_count=2,
        requires_proxy=False,  # Not usually needed for official sites
    )

    def __init__(self):
        """Initialize website crawler."""
        super().__init__()
        self.phone_extractor = PhoneExtractor()
        self.text_cleaner = TextCleaner()

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Not implemented for website crawler.

        Website crawler is used for enrichment only.
        """
        logger.warning("website_crawler_search_not_supported")
        return []

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data by crawling official website.

        Args:
            company_data: Must include 'website' and 'company_name'

        Returns:
            Enriched source result or None
        """
        website = company_data.get("website")
        company_name = company_data.get("company_name")

        if not website or not company_name:
            return None

        # Normalize website URL
        normalized_url = WebsiteNormalizer.normalize(website)
        if not normalized_url:
            logger.debug("invalid_website_url", url=website)
            return None

        # Find and crawl contact pages
        contact_info = await self._crawl_contact_pages(normalized_url, company_name)

        if not contact_info:
            return None

        return SourceResult(
            source_name=self.source_name,
            company_name=company_name,
            website=normalized_url,
            phone=contact_info.get("phone"),
            address_line=contact_info.get("address"),
            source_url=contact_info.get("source_url"),
            raw_data=contact_info,
        )

    async def _crawl_contact_pages(
        self, base_url: str, company_name: str
    ) -> dict[str, Any] | None:
        """Crawl contact pages on a website.

        Args:
            base_url: Base website URL
            company_name: Company name for validation

        Returns:
            Dict with extracted contact info or None
        """
        contact_info: dict[str, Any] = {}
        pages_crawled = 0
        max_pages = settings.max_pages_per_domain

        try:
            async with httpx.AsyncClient(
                timeout=settings.request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": settings.user_agent},
            ) as client:
                # Try common contact page URLs
                for pattern in self.CONTACT_URL_PATTERNS:
                    if pages_crawled >= max_pages:
                        break

                    contact_url = urljoin(base_url, pattern)

                    try:
                        response = await client.get(contact_url)
                        if response.status_code == 200:
                            pages_crawled += 1
                            extracted = self._extract_contact_info(
                                response.text, contact_url, company_name
                            )

                            # Merge extracted info
                            if extracted.get("phone") and not contact_info.get("phone"):
                                contact_info["phone"] = extracted["phone"]
                                contact_info["source_url"] = contact_url

                            if extracted.get("address") and not contact_info.get("address"):
                                contact_info["address"] = extracted["address"]

                            logger.debug(
                                "contact_page_crawled",
                                url=contact_url,
                                found_phone=bool(extracted.get("phone")),
                                found_address=bool(extracted.get("address")),
                            )

                            # Stop if we found both phone and address
                            if contact_info.get("phone") and contact_info.get("address"):
                                break

                    except httpx.HTTPError:
                        # Page doesn't exist or is inaccessible, continue
                        continue

        except Exception as e:
            self.log_error("crawl_contact_pages", e)
            return None

        return contact_info if contact_info else None

    def _extract_contact_info(
        self, html: str, url: str, company_name: str
    ) -> dict[str, Any]:
        """Extract contact information from HTML.

        Args:
            html: HTML content
            url: Page URL
            company_name: Company name for context

        Returns:
            Dict with extracted data
        """
        result: dict[str, Any] = {}

        # Parse HTML
        parser = HTMLParser(html)

        # Extract text content
        text_content = self.text_cleaner.clean_html(html)

        # Extract phone numbers
        phones = self.phone_extractor.extract_and_normalize(text_content)
        if phones:
            # Take the first valid phone
            result["phone"] = phones[0]["normalized"]

        # Extract address (simplified heuristic)
        # Look for patterns like "Via", "Piazza", postal codes
        address_match = re.search(
            r"(?:via|piazza|viale|corso|strada)\s+[^,\n]{5,50}(?:,\s*\d{5})?",
            text_content,
            re.IGNORECASE,
        )
        if address_match:
            result["address"] = address_match.group(0).strip()

        return result
