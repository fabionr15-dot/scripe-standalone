"""Data normalization utilities."""

import re
from urllib.parse import urlparse


class WebsiteNormalizer:
    """Normalize and validate website URLs."""

    @staticmethod
    def normalize(url: str) -> str | None:
        """Normalize a website URL.

        Args:
            url: Raw URL

        Returns:
            Normalized URL with scheme, or None if invalid
        """
        if not url:
            return None

        url = url.strip().lower()

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return None

            # Remove trailing slash
            path = parsed.path.rstrip("/")
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"

            return normalized
        except Exception:
            return None

    @staticmethod
    def extract_domain(url: str) -> str | None:
        """Extract domain from URL.

        Args:
            url: URL

        Returns:
            Domain name
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None


class AddressNormalizer:
    """Normalize address components."""

    @staticmethod
    def normalize_postal_code(postal_code: str, country: str = "IT") -> str | None:
        """Normalize postal code.

        Args:
            postal_code: Raw postal code
            country: Country code

        Returns:
            Normalized postal code
        """
        if not postal_code:
            return None

        postal_code = postal_code.strip().upper()

        # Italian postal codes: 5 digits
        if country == "IT":
            digits = re.sub(r"\D", "", postal_code)
            if len(digits) == 5:
                return digits

        return postal_code

    @staticmethod
    def normalize_city(city: str) -> str | None:
        """Normalize city name.

        Args:
            city: Raw city name

        Returns:
            Normalized city name
        """
        if not city:
            return None

        # Title case and remove extra spaces
        city = " ".join(city.strip().title().split())
        return city

    @staticmethod
    def normalize_region(region: str) -> str | None:
        """Normalize region/state name.

        Args:
            region: Raw region name

        Returns:
            Normalized region name
        """
        if not region:
            return None

        region = " ".join(region.strip().title().split())
        return region


class CompanyNameNormalizer:
    """Normalize company names."""

    LEGAL_SUFFIXES = [
        "s.p.a.",
        "spa",
        "s.r.l.",
        "srl",
        "s.a.s.",
        "sas",
        "s.n.c.",
        "snc",
        "s.s.",
        "ltd",
        "llc",
        "inc",
        "corp",
        "gmbh",
    ]

    @staticmethod
    def normalize(name: str) -> str | None:
        """Normalize company name for comparison.

        Args:
            name: Raw company name

        Returns:
            Normalized name
        """
        if not name:
            return None

        # Basic cleanup
        name = name.strip()
        name = re.sub(r"\s+", " ", name)

        return name

    @staticmethod
    def normalize_for_deduplication(name: str) -> str | None:
        """Normalize company name for deduplication matching.

        Args:
            name: Raw company name

        Returns:
            Normalized name for matching (lowercase, no punctuation, no legal suffixes)
        """
        if not name:
            return None

        name = name.lower().strip()

        # Remove punctuation
        name = re.sub(r"[^\w\s]", " ", name)

        # Remove legal suffixes
        for suffix in CompanyNameNormalizer.LEGAL_SUFFIXES:
            pattern = r"\b" + re.escape(suffix) + r"\b"
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        # Remove extra whitespace
        name = re.sub(r"\s+", " ", name).strip()

        return name


class TextCleaner:
    """Clean and extract text from HTML and other formats."""

    @staticmethod
    def clean_html(html: str) -> str:
        """Remove HTML tags and clean text.

        Args:
            html: HTML content

        Returns:
            Clean text
        """
        # Remove script and style tags
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Decode common HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")

        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    @staticmethod
    def extract_snippet(text: str, max_length: int = 200) -> str:
        """Extract a snippet from text.

        Args:
            text: Full text
            max_length: Maximum snippet length

        Returns:
            Truncated snippet
        """
        if not text:
            return ""

        text = text.strip()
        if len(text) <= max_length:
            return text

        return text[:max_length].rsplit(" ", 1)[0] + "..."
