"""Phone number extraction and normalization."""

import re
from typing import Any

import phonenumbers
from phonenumbers import NumberParseException

from scripe.logging_config import get_logger

logger = get_logger(__name__)


class PhoneExtractor:
    """Extract and normalize phone numbers."""

    # Common Italian phone patterns
    PATTERNS = [
        # Italian mobile: +39 3XX XXXXXXX or 3XX XXXXXXX
        r"\+?39[\s\-]?3\d{2}[\s\-]?\d{6,7}",
        # Italian landline: +39 0X XXXXXXXX or 0X XXXXXXXX
        r"\+?39[\s\-]?0\d{1,3}[\s\-]?\d{6,8}",
        # Generic international: +XX XXX XXXXXXX
        r"\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{6,10}",
        # Simple patterns with common separators
        r"\d{2,4}[\s\-\.\/]\d{6,10}",
        r"\(\d{2,4}\)[\s\-]?\d{6,10}",
    ]

    def __init__(self, default_region: str = "IT"):
        self.default_region = default_region

    def extract_from_text(self, text: str) -> list[str]:
        """Extract phone numbers from text."""
        if not text:
            return []

        phones = []
        for pattern in self.PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group(0)
                normalized = self.normalize(phone)
                if normalized:
                    phones.append(normalized)

        return list(set(phones))  # Remove duplicates

    def normalize(self, phone: str) -> str | None:
        """Normalize phone number to E.164 format."""
        if not phone:
            return None

        # Clean common formatting
        cleaned = re.sub(r"[\s\-\.\(\)\/]", "", phone)

        try:
            # Parse with phonenumbers library
            parsed = phonenumbers.parse(cleaned, self.default_region)

            # Validate
            if not phonenumbers.is_valid_number(parsed):
                logger.debug("invalid_phone_number", phone=phone)
                return None

            # Format to E.164
            normalized = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            return normalized

        except NumberParseException as e:
            logger.debug("phone_parse_error", phone=phone, error=str(e))
            return None

    def is_valid(self, phone: str) -> bool:
        """Check if phone number is valid."""
        return self.normalize(phone) is not None

    def get_type(self, phone: str) -> str | None:
        """Get phone number type (mobile, fixed_line, etc.)."""
        try:
            parsed = phonenumbers.parse(phone, self.default_region)
            number_type = phonenumbers.number_type(parsed)

            type_map = {
                phonenumbers.PhoneNumberType.MOBILE: "mobile",
                phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
                phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
                phonenumbers.PhoneNumberType.VOIP: "voip",
            }

            return type_map.get(number_type, "unknown")

        except NumberParseException:
            return None
