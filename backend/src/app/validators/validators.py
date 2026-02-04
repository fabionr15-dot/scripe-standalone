"""Optional validators for phone, email, and website.

These validators can be enabled/disabled per search.
"""

import asyncio
import re
import socket
from typing import Any

import httpx

from app.extractors.phone import PhoneExtractor
from app.logging_config import get_logger

logger = get_logger(__name__)


class PhoneValidator:
    """Validate phone numbers (optional, toggleable)."""

    def __init__(self):
        """Initialize phone validator."""
        self.extractor = PhoneExtractor()

    async def validate(self, phone: str, country: str = "IT") -> dict[str, Any]:
        """Validate phone number.

        Args:
            phone: Phone number to validate
            country: Country code

        Returns:
            Validation result dict
        """
        result = {
            "valid": False,
            "formatted": None,
            "type": None,  # mobile, landline, voip
            "carrier": None,
            "score": 0,
        }

        # Format validation
        normalized = self.extractor.normalize(phone, country)
        if not normalized:
            return result

        result["valid"] = True
        result["formatted"] = normalized
        result["score"] = 60

        # Note: Full carrier lookup requires paid APIs (Twilio, Nexmo, etc.)
        # This is a placeholder for when API is configured
        # For now, basic heuristics

        # Italian mobile numbers start with 3
        if normalized.startswith("+393"):
            result["type"] = "mobile"
            result["score"] += 20  # Mobile preferred for cold calling
        elif normalized.startswith("+390"):
            result["type"] = "landline"
            result["score"] += 10

        return result


class EmailValidator:
    """Validate email addresses (optional, toggleable)."""

    async def validate(self, email: str, check_smtp: bool = False) -> dict[str, Any]:
        """Validate email address.

        Args:
            email: Email to validate
            check_smtp: Whether to check SMTP (slow, can trigger spam filters)

        Returns:
            Validation result dict
        """
        result = {
            "valid": False,
            "deliverable": None,
            "disposable": False,
            "role_based": False,
            "score": 0,
        }

        # Format validation
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.match(email_regex, email, re.IGNORECASE):
            return result

        result["valid"] = True
        result["score"] = 40

        # Check disposable domains
        disposable_domains = [
            "tempmail.com", "guerrillamail.com", "10minutemail.com",
            "throwaway.email", "yopmail.com", "mailinator.com",
            "temp-mail.org", "sharklasers.com"
        ]
        domain = email.split('@')[1].lower()
        if domain in disposable_domains:
            result["disposable"] = True
            result["score"] = 10
            return result

        result["score"] += 20

        # Check role-based
        local = email.split('@')[0].lower()
        role_accounts = ["info", "contact", "support", "admin", "sales", "noreply"]
        if local in role_accounts:
            result["role_based"] = True
            result["score"] += 10  # Still useful for business
        else:
            result["score"] += 30  # Personal email better for outreach

        # DNS MX record check (fast)
        try:
            mx_records = await self._check_mx_records(domain)
            if mx_records:
                result["deliverable"] = True
                result["score"] += 10
        except Exception as e:
            logger.debug("mx_check_failed", domain=domain, error=str(e))

        # SMTP check (optional, slow)
        if check_smtp and result["deliverable"]:
            # Note: This requires async SMTP library and can be blocked
            # Placeholder for future implementation
            pass

        return result

    async def _check_mx_records(self, domain: str) -> list[str]:
        """Check if domain has MX records.

        Args:
            domain: Domain to check

        Returns:
            List of MX records
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            mx_records = await loop.run_in_executor(
                None,
                lambda: socket.getaddrinfo(domain, None)
            )
            return [str(r) for r in mx_records] if mx_records else []
        except Exception:
            return []


class WebsiteValidator:
    """Validate website URLs (optional, toggleable)."""

    async def validate(self, url: str, timeout: int = 10) -> dict[str, Any]:
        """Validate website is active and accessible.

        Args:
            url: Website URL
            timeout: Request timeout in seconds

        Returns:
            Validation result dict
        """
        result = {
            "valid": False,
            "accessible": False,
            "ssl_valid": False,
            "response_time": None,
            "status_code": None,
            "redirects_to": None,
            "score": 0,
        }

        if not url:
            return result

        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        result["valid"] = True
        result["score"] = 20

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
                verify=True  # Check SSL
            ) as client:
                import time
                start_time = time.time()

                response = await client.head(url)

                result["response_time"] = time.time() - start_time
                result["status_code"] = response.status_code

                # Check if accessible
                if 200 <= response.status_code < 300:
                    result["accessible"] = True
                    result["score"] += 40

                    # SSL valid if using https
                    if url.startswith('https://'):
                        result["ssl_valid"] = True
                        result["score"] += 20

                    # Fast response time bonus
                    if result["response_time"] < 2.0:
                        result["score"] += 10
                    elif result["response_time"] < 5.0:
                        result["score"] += 5

                # Check redirects
                if response.history:
                    result["redirects_to"] = str(response.url)
                    # Penalize if redirects to different domain
                    original_domain = url.split('/')[2]
                    final_domain = str(response.url).split('/')[2]
                    if original_domain != final_domain:
                        result["score"] -= 20

        except httpx.TimeoutException:
            logger.debug("website_timeout", url=url)
            result["score"] = 10
        except httpx.SSLError:
            logger.debug("website_ssl_error", url=url)
            result["ssl_valid"] = False
            result["score"] = 15
        except Exception as e:
            logger.debug("website_validation_error", url=url, error=str(e))

        # Ensure score is 0-100
        result["score"] = max(0, min(100, result["score"]))

        return result
