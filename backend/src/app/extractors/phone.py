"""Phone number extraction and normalization."""

import re
from typing import Any

import phonenumbers
from phonenumbers import NumberParseException

from app.logging_config import get_logger

logger = get_logger(__name__)


class PhoneExtractor:
    """Extract and normalize phone numbers."""

    # Regex patterns for common phone formats
    PHONE_PATTERNS = [
        # Italian formats
        r"\+39[\s\-]?\d{2,3}[\s\-]?\d{6,7}",
        r"\+39[\s\-]?\d{3}[\s\-]?\d{7}",
        r"0\d{2,3}[\s\-]?\d{6,7}",
        # International format
        r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}",
        # Generic
        r"\d{3}[\s\-]?\d{3}[\s\-]?\d{4}",
        r"\(\d{2,4}\)[\s\-]?\d{6,8}",
    ]

    def __init__(self, default_region: str = "IT"):
        """Initialize phone extractor.

        Args:
            default_region: Default country code for parsing (ISO 3166-1 alpha-2)
        """
        self.default_region = default_region

    def extract_from_text(self, text: str) -> list[str]:
        """Extract phone numbers from text.

        Args:
            text: Text to search

        Returns:
            List of found phone numbers (raw)
        """
        if not text:
            return []

        phones = []
        for pattern in self.PHONE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phones.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_phones = []
        for phone in phones:
            normalized = re.sub(r"[\s\-\(\)]", "", phone)
            if normalized not in seen:
                seen.add(normalized)
                unique_phones.append(phone)

        return unique_phones

    def normalize(self, phone: str, region: str | None = None) -> str | None:
        """Normalize phone number to E.164 format.

        Args:
            phone: Raw phone number
            region: Country code (defaults to instance default)

        Returns:
            Normalized phone in E.164 format, or None if invalid
        """
        if not phone:
            return None

        region = region or self.default_region

        try:
            parsed = phonenumbers.parse(phone, region)
            if phonenumbers.is_valid_number(parsed):
                normalized = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                logger.debug("phone_normalized", original=phone, normalized=normalized)
                return normalized
            else:
                logger.debug("phone_invalid", phone=phone, region=region)
                return None
        except NumberParseException as e:
            logger.debug("phone_parse_error", phone=phone, error=str(e))
            return None

    def extract_and_normalize(
        self, text: str, region: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract and normalize phone numbers from text.

        Args:
            text: Text to search
            region: Country code

        Returns:
            List of dicts with 'raw' and 'normalized' keys
        """
        raw_phones = self.extract_from_text(text)
        results = []

        for raw in raw_phones:
            normalized = self.normalize(raw, region)
            if normalized:
                results.append({"raw": raw, "normalized": normalized})

        return results

    def validate(self, phone: str, region: str | None = None) -> bool:
        """Validate if a phone number is valid.

        Args:
            phone: Phone number to validate
            region: Country code

        Returns:
            True if valid
        """
        region = region or self.default_region
        try:
            parsed = phonenumbers.parse(phone, region)
            return phonenumbers.is_valid_number(parsed)
        except NumberParseException:
            return False
