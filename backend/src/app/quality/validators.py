"""Data validators for phone, email, and website validation."""

import asyncio
import re
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType, carrier, geocoder

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    confidence: float  # 0-1
    details: dict[str, Any]
    error: str | None = None


class PhoneValidator:
    """Validates phone numbers using various methods.

    Validation levels:
    1. Format validation (free) - Check if number format is valid
    2. Carrier lookup (free) - Identify carrier/type
    3. Line type check (free) - Mobile vs landline
    4. Carrier API check (paid) - Real-time validation
    """

    def __init__(self, default_country: str = "IT"):
        """Initialize phone validator.

        Args:
            default_country: Default country code for parsing
        """
        self.default_country = default_country
        self.logger = get_logger(__name__)

    def validate_format(self, phone: str, country: str | None = None) -> ValidationResult:
        """Validate phone number format.

        Args:
            phone: Phone number string
            country: Optional country code

        Returns:
            Validation result
        """
        country = country or self.default_country

        try:
            # Parse number
            parsed = phonenumbers.parse(phone, country)

            # Check if valid
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)

            # Get formatted versions
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            international = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            national = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            )

            # Get number type
            number_type = phonenumbers.number_type(parsed)
            type_name = self._get_type_name(number_type)

            # Get region
            region = geocoder.description_for_number(parsed, "en")

            # Get carrier if available
            carrier_name = carrier.name_for_number(parsed, "en")

            return ValidationResult(
                is_valid=is_valid,
                confidence=0.9 if is_valid else (0.5 if is_possible else 0.1),
                details={
                    "e164": e164,
                    "international": international,
                    "national": national,
                    "country_code": parsed.country_code,
                    "number_type": type_name,
                    "region": region,
                    "carrier": carrier_name,
                    "is_possible": is_possible,
                },
            )

        except NumberParseException as e:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                details={},
                error=str(e),
            )

    def _get_type_name(self, number_type: PhoneNumberType) -> str:
        """Get human-readable type name."""
        type_names = {
            PhoneNumberType.FIXED_LINE: "landline",
            PhoneNumberType.MOBILE: "mobile",
            PhoneNumberType.FIXED_LINE_OR_MOBILE: "landline_or_mobile",
            PhoneNumberType.TOLL_FREE: "toll_free",
            PhoneNumberType.PREMIUM_RATE: "premium_rate",
            PhoneNumberType.SHARED_COST: "shared_cost",
            PhoneNumberType.VOIP: "voip",
            PhoneNumberType.PERSONAL_NUMBER: "personal",
            PhoneNumberType.PAGER: "pager",
            PhoneNumberType.UAN: "uan",
            PhoneNumberType.VOICEMAIL: "voicemail",
            PhoneNumberType.UNKNOWN: "unknown",
        }
        return type_names.get(number_type, "unknown")

    async def validate_carrier(self, phone: str, country: str | None = None) -> ValidationResult:
        """Validate phone with carrier lookup.

        Note: This is a more expensive validation that may require API calls.

        Args:
            phone: Phone number
            country: Country code

        Returns:
            Validation result with carrier info
        """
        # First do format validation
        format_result = self.validate_format(phone, country)

        if not format_result.is_valid:
            return format_result

        # For now, carrier info from phonenumbers library is sufficient
        # In production, integrate with carrier lookup APIs like Twilio or NumVerify

        details = format_result.details.copy()
        details["carrier_verified"] = bool(details.get("carrier"))

        return ValidationResult(
            is_valid=format_result.is_valid,
            confidence=0.95 if details.get("carrier_verified") else 0.8,
            details=details,
        )


class EmailValidator:
    """Validates email addresses using various methods.

    Validation levels:
    1. Format validation (free) - Regex check
    2. MX record check (free) - Verify domain has mail server
    3. SMTP check (free but slow) - Verify mailbox exists
    """

    # Email regex pattern (simplified but effective)
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "10minutemail.com", "mailinator.com", "trashmail.com",
        "yopmail.com", "fakeinbox.com", "sharklasers.com",
    }

    # Common typo domains
    TYPO_DOMAINS = {
        "gmial.com": "gmail.com",
        "gmai.com": "gmail.com",
        "gamil.com": "gmail.com",
        "hotmai.com": "hotmail.com",
        "hotnail.com": "hotmail.com",
        "yahooo.com": "yahoo.com",
        "yaho.com": "yahoo.com",
    }

    def __init__(self):
        """Initialize email validator."""
        self.logger = get_logger(__name__)
        self._mx_cache: dict[str, list[str]] = {}

    def validate_format(self, email: str) -> ValidationResult:
        """Validate email format.

        Args:
            email: Email address

        Returns:
            Validation result
        """
        email = email.strip().lower()

        # Check format
        if not self.EMAIL_PATTERN.match(email):
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                details={"reason": "invalid_format"},
                error="Invalid email format",
            )

        # Extract domain
        domain = email.split("@")[1]

        # Check for disposable domains
        if domain in self.DISPOSABLE_DOMAINS:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                details={"reason": "disposable_domain", "domain": domain},
                error="Disposable email domain",
            )

        # Check for typo domains
        if domain in self.TYPO_DOMAINS:
            suggested = self.TYPO_DOMAINS[domain]
            return ValidationResult(
                is_valid=False,
                confidence=0.3,
                details={
                    "reason": "typo_domain",
                    "domain": domain,
                    "suggested": email.replace(domain, suggested),
                },
                error=f"Possible typo: did you mean {suggested}?",
            )

        return ValidationResult(
            is_valid=True,
            confidence=0.7,
            details={
                "email": email,
                "domain": domain,
                "format_valid": True,
            },
        )

    async def validate_mx(self, email: str) -> ValidationResult:
        """Validate email with MX record check.

        Args:
            email: Email address

        Returns:
            Validation result
        """
        # First check format
        format_result = self.validate_format(email)
        if not format_result.is_valid:
            return format_result

        domain = email.split("@")[1]

        # Check cache
        if domain in self._mx_cache:
            mx_records = self._mx_cache[domain]
        else:
            # Look up MX records
            mx_records = await self._get_mx_records(domain)
            self._mx_cache[domain] = mx_records

        if not mx_records:
            return ValidationResult(
                is_valid=False,
                confidence=0.2,
                details={
                    "email": email,
                    "domain": domain,
                    "mx_records": [],
                    "reason": "no_mx_records",
                },
                error="Domain has no MX records",
            )

        return ValidationResult(
            is_valid=True,
            confidence=0.85,
            details={
                "email": email,
                "domain": domain,
                "mx_records": mx_records[:3],  # First 3 MX records
                "mx_verified": True,
            },
        )

    async def _get_mx_records(self, domain: str) -> list[str]:
        """Get MX records for domain.

        Args:
            domain: Domain name

        Returns:
            List of MX record hostnames
        """
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, "MX")
            return sorted(
                [(r.preference, str(r.exchange).rstrip(".")) for r in answers],
                key=lambda x: x[0]
            )
        except Exception:
            # Fallback to socket
            try:
                # Try to resolve the domain (simplified check)
                socket.gethostbyname(domain)
                return [domain]  # Domain exists, assume it can receive mail
            except socket.gaierror:
                return []

    async def validate_smtp(self, email: str, timeout: int = 10) -> ValidationResult:
        """Validate email with SMTP check.

        Warning: This is slow and may be blocked by some servers.

        Args:
            email: Email address
            timeout: Timeout in seconds

        Returns:
            Validation result
        """
        # First validate MX
        mx_result = await self.validate_mx(email)
        if not mx_result.is_valid:
            return mx_result

        # SMTP validation is expensive and often blocked
        # For production, consider using a service like ZeroBounce or NeverBounce

        # For now, return MX result with note about SMTP
        details = mx_result.details.copy()
        details["smtp_check"] = "skipped"
        details["note"] = "SMTP validation requires external service"

        return ValidationResult(
            is_valid=True,
            confidence=0.85,  # Can't increase without actual SMTP check
            details=details,
        )


class WebsiteValidator:
    """Validates website URLs.

    Validation levels:
    1. Format validation (free) - URL format check
    2. DNS resolution (free) - Check domain resolves
    3. HTTP check (free) - Check site responds
    4. SSL check (free) - Verify HTTPS works
    """

    # Common non-business domains to flag
    GENERIC_DOMAINS = {
        "facebook.com", "instagram.com", "twitter.com", "linkedin.com",
        "youtube.com", "tiktok.com", "pinterest.com",
        "google.com", "bing.com", "yahoo.com",
        "wikipedia.org", "amazon.com", "ebay.com",
    }

    def __init__(self):
        """Initialize website validator."""
        self.logger = get_logger(__name__)

    def validate_format(self, url: str) -> ValidationResult:
        """Validate URL format.

        Args:
            url: Website URL

        Returns:
            Validation result
        """
        url = url.strip()

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urlparse(url)

            # Check required components
            if not parsed.netloc:
                return ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    details={"reason": "no_domain"},
                    error="URL has no domain",
                )

            # Check for valid TLD
            domain_parts = parsed.netloc.split(".")
            if len(domain_parts) < 2:
                return ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    details={"reason": "invalid_domain"},
                    error="Invalid domain format",
                )

            # Check for generic domains
            domain = parsed.netloc.lower()
            if any(generic in domain for generic in self.GENERIC_DOMAINS):
                return ValidationResult(
                    is_valid=True,
                    confidence=0.5,
                    details={
                        "url": url,
                        "domain": domain,
                        "warning": "generic_platform",
                    },
                )

            return ValidationResult(
                is_valid=True,
                confidence=0.7,
                details={
                    "url": url,
                    "domain": domain,
                    "scheme": parsed.scheme,
                    "path": parsed.path,
                },
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                details={},
                error=str(e),
            )

    async def validate_http(self, url: str, timeout: int = 10) -> ValidationResult:
        """Validate website with HTTP check.

        Args:
            url: Website URL
            timeout: Timeout in seconds

        Returns:
            Validation result
        """
        # First check format
        format_result = self.validate_format(url)
        if not format_result.is_valid:
            return format_result

        url = format_result.details.get("url", url)

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
            ) as client:
                response = await client.head(url)

                # Check if successful
                is_valid = response.status_code < 400
                final_url = str(response.url)

                return ValidationResult(
                    is_valid=is_valid,
                    confidence=0.95 if is_valid else 0.3,
                    details={
                        "url": url,
                        "final_url": final_url,
                        "status_code": response.status_code,
                        "redirected": final_url != url,
                        "https": final_url.startswith("https://"),
                        "content_type": response.headers.get("content-type"),
                    },
                )

        except httpx.TimeoutException:
            return ValidationResult(
                is_valid=False,
                confidence=0.3,
                details={"url": url, "reason": "timeout"},
                error="Request timed out",
            )
        except httpx.ConnectError:
            return ValidationResult(
                is_valid=False,
                confidence=0.1,
                details={"url": url, "reason": "connection_failed"},
                error="Could not connect to server",
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                confidence=0.2,
                details={"url": url, "reason": "error"},
                error=str(e),
            )

    async def validate_ssl(self, url: str, timeout: int = 10) -> ValidationResult:
        """Validate website SSL certificate.

        Args:
            url: Website URL
            timeout: Timeout in seconds

        Returns:
            Validation result
        """
        # First do HTTP validation
        http_result = await self.validate_http(url, timeout)

        if not http_result.is_valid:
            return http_result

        # Check if HTTPS
        final_url = http_result.details.get("final_url", url)
        is_https = final_url.startswith("https://")

        details = http_result.details.copy()
        details["ssl_valid"] = is_https

        return ValidationResult(
            is_valid=True,
            confidence=0.98 if is_https else 0.85,
            details=details,
        )


class DataValidator:
    """Unified validator that combines all validators."""

    def __init__(self, default_country: str = "IT"):
        """Initialize data validator.

        Args:
            default_country: Default country for phone validation
        """
        self.phone_validator = PhoneValidator(default_country)
        self.email_validator = EmailValidator()
        self.website_validator = WebsiteValidator()
        self.logger = get_logger(__name__)

    async def validate_all(
        self,
        data: dict[str, Any],
        level: str = "standard",
    ) -> dict[str, ValidationResult]:
        """Validate all fields in data.

        Args:
            data: Data dictionary with phone, email, website fields
            level: Validation level (basic, standard, premium)

        Returns:
            Dict of field -> ValidationResult
        """
        results = {}
        tasks = []

        # Phone validation
        if data.get("phone"):
            if level == "basic":
                results["phone"] = self.phone_validator.validate_format(data["phone"])
            else:
                tasks.append(("phone", self.phone_validator.validate_carrier(
                    data["phone"], data.get("country")
                )))

        # Email validation
        if data.get("email"):
            if level == "basic":
                results["email"] = self.email_validator.validate_format(data["email"])
            elif level == "standard":
                tasks.append(("email", self.email_validator.validate_mx(data["email"])))
            else:  # premium
                tasks.append(("email", self.email_validator.validate_smtp(data["email"])))

        # Website validation
        if data.get("website"):
            if level == "basic":
                results["website"] = self.website_validator.validate_format(data["website"])
            else:
                tasks.append(("website", self.website_validator.validate_http(data["website"])))

        # Execute async tasks
        if tasks:
            task_results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            for (field, _), result in zip(tasks, task_results):
                if isinstance(result, Exception):
                    results[field] = ValidationResult(
                        is_valid=False,
                        confidence=0.0,
                        details={},
                        error=str(result),
                    )
                else:
                    results[field] = result

        return results
