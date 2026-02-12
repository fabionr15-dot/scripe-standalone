"""Hunter.io API integration for email finding and verification.

Hunter.io provides:
- Domain search: Find all emails associated with a domain
- Email finder: Find email for a specific person
- Email verifier: Verify if an email is deliverable

API Documentation: https://hunter.io/api-documentation/v2
"""

import httpx
from typing import Any
from urllib.parse import urlparse

from app.logging_config import get_logger
from app.settings import settings

logger = get_logger(__name__)


class HunterAPIError(Exception):
    """Error from Hunter.io API."""

    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class HunterService:
    """Service for interacting with Hunter.io API."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: str = None):
        """Initialize Hunter service.

        Args:
            api_key: Hunter.io API key. If not provided, uses settings.
        """
        self.api_key = api_key or getattr(settings, "HUNTER_API_KEY", "")
        self.enabled = bool(self.api_key)
        self.logger = get_logger(__name__)

    def _get_domain(self, url_or_domain: str) -> str:
        """Extract domain from URL or return as-is if already a domain.

        Args:
            url_or_domain: URL or domain string

        Returns:
            Domain string (e.g., 'example.com')
        """
        if not url_or_domain:
            return ""

        # If it looks like a URL, parse it
        if "://" in url_or_domain:
            parsed = urlparse(url_or_domain)
            domain = parsed.netloc
        else:
            domain = url_or_domain

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain.lower()

    async def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Make request to Hunter.io API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data

        Raises:
            HunterAPIError: If API returns an error
        """
        if not self.enabled:
            raise HunterAPIError("Hunter.io API is not configured", error_code="not_configured")

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, params=params)

                if response.status_code == 401:
                    raise HunterAPIError("Invalid API key", status_code=401, error_code="invalid_api_key")
                elif response.status_code == 429:
                    raise HunterAPIError("Rate limit exceeded", status_code=429, error_code="rate_limit")

                data = response.json()

                if "errors" in data:
                    error = data["errors"][0] if data["errors"] else {"details": "Unknown error"}
                    raise HunterAPIError(
                        error.get("details", "Unknown error"),
                        status_code=response.status_code,
                        error_code=error.get("code"),
                    )

                return data.get("data", {})

            except httpx.TimeoutException:
                raise HunterAPIError("Request timeout", error_code="timeout")
            except httpx.RequestError as e:
                raise HunterAPIError(f"Request failed: {str(e)}", error_code="request_error")

    async def domain_search(self, domain: str, limit: int = 10) -> list[dict]:
        """Search for all email addresses associated with a domain.

        Args:
            domain: Domain to search (e.g., 'example.com')
            limit: Maximum number of emails to return (default 10)

        Returns:
            List of email objects with format:
            {
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "position": "CEO",
                "department": "executive",
                "confidence": 95,
                "sources": [...]
            }
        """
        domain = self._get_domain(domain)
        if not domain:
            return []

        try:
            data = await self._request("GET", "domain-search", {
                "domain": domain,
                "limit": limit,
            })

            emails = data.get("emails", [])

            self.logger.info(
                "hunter_domain_search",
                domain=domain,
                emails_found=len(emails),
            )

            return emails

        except HunterAPIError as e:
            self.logger.warning(
                "hunter_domain_search_failed",
                domain=domain,
                error=str(e),
            )
            return []

    async def find_email(
        self,
        domain: str,
        first_name: str = None,
        last_name: str = None,
        full_name: str = None,
    ) -> dict | None:
        """Find email for a specific person at a company.

        Args:
            domain: Company domain
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)

        Returns:
            Email object or None if not found:
            {
                "email": "john.doe@example.com",
                "score": 95,
                "position": "CEO",
                "domain": "example.com",
                "sources": [...]
            }
        """
        domain = self._get_domain(domain)
        if not domain:
            return None

        params = {"domain": domain}

        if full_name:
            params["full_name"] = full_name
        else:
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name

        if not (full_name or first_name or last_name):
            return None

        try:
            data = await self._request("GET", "email-finder", params)

            if data.get("email"):
                self.logger.info(
                    "hunter_email_found",
                    domain=domain,
                    confidence=data.get("score", 0),
                )
                return data

            return None

        except HunterAPIError as e:
            self.logger.warning(
                "hunter_find_email_failed",
                domain=domain,
                error=str(e),
            )
            return None

    async def verify_email(self, email: str) -> dict:
        """Verify if an email address is deliverable.

        Args:
            email: Email address to verify

        Returns:
            Verification result:
            {
                "email": "john@example.com",
                "status": "valid",  # valid, invalid, accept_all, webmail, disposable, unknown
                "score": 95,
                "regexp": True,
                "gibberish": False,
                "disposable": False,
                "webmail": False,
                "mx_records": True,
                "smtp_server": True,
                "smtp_check": True,
                "accept_all": False,
                "block": False,
            }
        """
        if not email:
            return {"email": email, "status": "invalid", "score": 0}

        try:
            data = await self._request("GET", "email-verifier", {"email": email})

            self.logger.info(
                "hunter_email_verified",
                email=email,
                status=data.get("status"),
                score=data.get("score", 0),
            )

            return data

        except HunterAPIError as e:
            self.logger.warning(
                "hunter_verify_email_failed",
                email=email,
                error=str(e),
            )
            return {"email": email, "status": "unknown", "score": 0}

    async def get_account_info(self) -> dict:
        """Get account information including remaining credits.

        Returns:
            Account info:
            {
                "requests": {
                    "searches": {"used": 100, "available": 900},
                    "verifications": {"used": 50, "available": 950}
                },
                "reset_date": "2024-02-01"
            }
        """
        try:
            data = await self._request("GET", "account")
            return data
        except HunterAPIError:
            return {}

    async def enrich_company_emails(self, website: str, company_name: str = None) -> dict:
        """Enrich a company with email information.

        This is a convenience method that:
        1. Searches for all emails on the domain
        2. Returns structured data suitable for the Company model

        Args:
            website: Company website URL
            company_name: Optional company name for better matching

        Returns:
            Enrichment result:
            {
                "contact_emails": [
                    {"email": "...", "name": "...", "position": "...", "confidence": 95}
                ],
                "email_pattern": "{first}.{last}@domain.com",
                "organization": "Company Name",
            }
        """
        domain = self._get_domain(website)
        if not domain:
            return {"contact_emails": [], "email_pattern": None, "organization": None}

        try:
            data = await self._request("GET", "domain-search", {
                "domain": domain,
                "limit": 5,  # Get top 5 emails
            })

            # Format emails for our model
            contact_emails = []
            for email_data in data.get("emails", []):
                contact_emails.append({
                    "email": email_data.get("value"),
                    "name": f"{email_data.get('first_name', '')} {email_data.get('last_name', '')}".strip(),
                    "position": email_data.get("position"),
                    "department": email_data.get("department"),
                    "confidence": email_data.get("confidence", 0),
                })

            return {
                "contact_emails": contact_emails,
                "email_pattern": data.get("pattern"),
                "organization": data.get("organization"),
                "domain": domain,
            }

        except HunterAPIError:
            return {"contact_emails": [], "email_pattern": None, "organization": None}


# Singleton instance
hunter_service = HunterService()
