"""Website extraction and normalization."""

import re
from urllib.parse import urlparse

from scripe.logging_config import get_logger

logger = get_logger(__name__)


class WebsiteExtractor:
    """Extract and normalize website URLs."""

    # URL patterns
    URL_PATTERN = re.compile(
        r"(?:http[s]?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:/[^\s]*)?)",
        re.IGNORECASE,
    )

    def extract_from_text(self, text: str) -> list[str]:
        """Extract URLs from text."""
        if not text:
            return []

        urls = []
        matches = self.URL_PATTERN.finditer(text)

        for match in matches:
            url = match.group(0)
            normalized = self.normalize(url)
            if normalized:
                urls.append(normalized)

        return list(set(urls))

    def normalize(self, url: str) -> str | None:
        """Normalize URL to standard format."""
        if not url:
            return None

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urlparse(url)

            # Validate
            if not parsed.netloc:
                return None

            # Remove www prefix for consistency
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            # Rebuild URL
            normalized = f"https://{netloc}"

            # Add path if present and not just '/'
            if parsed.path and parsed.path != "/":
                normalized += parsed.path

            return normalized

        except Exception as e:
            logger.debug("url_parse_error", url=url, error=str(e))
            return None

    def get_domain(self, url: str) -> str | None:
        """Extract domain from URL."""
        normalized = self.normalize(url)
        if not normalized:
            return None

        try:
            parsed = urlparse(normalized)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return None

    def is_valid(self, url: str) -> bool:
        """Check if URL is valid."""
        return self.normalize(url) is not None
