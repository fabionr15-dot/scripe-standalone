"""Address extraction and normalization."""

import re
from typing import Any

from scripe.logging_config import get_logger

logger = get_logger(__name__)


class AddressExtractor:
    """Extract and normalize addresses."""

    # Italian postal code pattern
    POSTAL_CODE_PATTERN = re.compile(r"\b\d{5}\b")

    # Common Italian provinces/cities
    MAJOR_CITIES = {
        "milano", "roma", "torino", "napoli", "palermo", "genova", "bologna",
        "firenze", "bari", "catania", "venezia", "verona", "messina", "padova",
        "trieste", "brescia", "parma", "modena", "reggio emilia", "perugia",
    }

    def __init__(self, default_country: str = "IT"):
        self.default_country = default_country

    def extract_postal_code(self, text: str) -> str | None:
        """Extract postal code from text."""
        if not text:
            return None

        match = self.POSTAL_CODE_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_city(self, text: str) -> str | None:
        """Extract city name from text."""
        if not text:
            return None

        text_lower = text.lower()

        # Try to find known cities
        for city in self.MAJOR_CITIES:
            if city in text_lower:
                return city.title()

        # Extract words that might be city names (capitalized words)
        words = text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 3:
                # Skip common words
                if word.lower() not in {"via", "viale", "corso", "piazza"}:
                    return word

        return None

    def normalize_address(self, address: str) -> str:
        """Normalize address string."""
        if not address:
            return ""

        # Remove extra whitespace
        normalized = " ".join(address.split())

        # Capitalize first letter of each word
        normalized = normalized.title()

        return normalized

    def parse_address(self, text: str) -> dict[str, str | None]:
        """Parse address components from text."""
        result: dict[str, str | None] = {
            "address_line": None,
            "postal_code": None,
            "city": None,
            "region": None,
            "country": self.default_country,
        }

        if not text:
            return result

        # Extract postal code
        postal_code = self.extract_postal_code(text)
        if postal_code:
            result["postal_code"] = postal_code

        # Extract city
        city = self.extract_city(text)
        if city:
            result["city"] = city

        # Full address as fallback
        result["address_line"] = self.normalize_address(text)

        return result
