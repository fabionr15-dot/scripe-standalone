"""HubSpot CRM integration service.

Provides OAuth authentication and contact management for HubSpot.

API Documentation: https://developers.hubspot.com/docs/api/overview
"""

import httpx
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from app.logging_config import get_logger
from app.settings import settings
from app.storage.db import db

logger = get_logger(__name__)


class HubSpotError(Exception):
    """Error from HubSpot API."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class HubSpotService:
    """Service for interacting with HubSpot CRM."""

    AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    API_URL = "https://api.hubapi.com"

    # Required scopes for our integration
    SCOPES = [
        "crm.objects.contacts.read",
        "crm.objects.contacts.write",
        "crm.objects.companies.read",
        "crm.objects.companies.write",
    ]

    def __init__(self):
        """Initialize HubSpot service."""
        self.client_id = getattr(settings, "HUBSPOT_CLIENT_ID", "")
        self.client_secret = getattr(settings, "HUBSPOT_CLIENT_SECRET", "")
        self.redirect_uri = getattr(settings, "HUBSPOT_REDIRECT_URI", "")
        self.enabled = bool(self.client_id and self.client_secret)
        self.logger = get_logger(__name__)

    def get_auth_url(self, user_id: int, state: str = None) -> str:
        """Generate OAuth authorization URL.

        Args:
            user_id: User ID to associate with this authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if not self.enabled:
            raise HubSpotError("HubSpot integration is not configured")

        # Generate state if not provided (for CSRF protection)
        if not state:
            state = f"{user_id}_{secrets.token_urlsafe(16)}"

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
            "state": state,
        }

        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token data:
            {
                "access_token": "...",
                "refresh_token": "...",
                "expires_in": 1800,
                "token_type": "bearer"
            }
        """
        if not self.enabled:
            raise HubSpotError("HubSpot integration is not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
            )

            if response.status_code != 200:
                raise HubSpotError(f"Token exchange failed: {response.text}", response.status_code)

            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authorization

        Returns:
            New token data
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                raise HubSpotError(f"Token refresh failed: {response.text}", response.status_code)

            return response.json()

    async def _request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        json_data: dict = None,
        params: dict = None,
    ) -> dict:
        """Make authenticated request to HubSpot API.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            access_token: OAuth access token
            json_data: JSON body for POST/PUT
            params: Query parameters

        Returns:
            Response data
        """
        url = f"{self.API_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json_data,
                params=params,
            )

            if response.status_code == 401:
                raise HubSpotError("Access token expired or invalid", 401)
            elif response.status_code >= 400:
                raise HubSpotError(f"API error: {response.text}", response.status_code)

            if response.content:
                return response.json()
            return {}

    async def create_contact(self, access_token: str, contact_data: dict) -> dict:
        """Create a new contact in HubSpot.

        Args:
            access_token: OAuth access token
            contact_data: Contact properties:
                {
                    "email": "john@example.com",
                    "firstname": "John",
                    "lastname": "Doe",
                    "phone": "+1234567890",
                    "company": "Acme Inc",
                    "website": "https://acme.com",
                    "city": "New York",
                    "country": "US",
                }

        Returns:
            Created contact with HubSpot ID
        """
        payload = {
            "properties": contact_data
        }

        result = await self._request(
            "POST",
            "crm/v3/objects/contacts",
            access_token,
            json_data=payload,
        )

        self.logger.info(
            "hubspot_contact_created",
            contact_id=result.get("id"),
            email=contact_data.get("email"),
        )

        return result

    async def create_company(self, access_token: str, company_data: dict) -> dict:
        """Create a new company in HubSpot.

        Args:
            access_token: OAuth access token
            company_data: Company properties:
                {
                    "name": "Acme Inc",
                    "domain": "acme.com",
                    "phone": "+1234567890",
                    "city": "New York",
                    "country": "US",
                    "industry": "Technology",
                }

        Returns:
            Created company with HubSpot ID
        """
        payload = {
            "properties": company_data
        }

        result = await self._request(
            "POST",
            "crm/v3/objects/companies",
            access_token,
            json_data=payload,
        )

        self.logger.info(
            "hubspot_company_created",
            company_id=result.get("id"),
            name=company_data.get("name"),
        )

        return result

    async def bulk_create_contacts(
        self,
        access_token: str,
        contacts: list[dict],
    ) -> list[dict]:
        """Batch create multiple contacts.

        Args:
            access_token: OAuth access token
            contacts: List of contact property dicts

        Returns:
            List of created contacts
        """
        # HubSpot batch endpoint accepts up to 100 contacts
        BATCH_SIZE = 100
        results = []

        for i in range(0, len(contacts), BATCH_SIZE):
            batch = contacts[i:i + BATCH_SIZE]
            payload = {
                "inputs": [{"properties": c} for c in batch]
            }

            try:
                result = await self._request(
                    "POST",
                    "crm/v3/objects/contacts/batch/create",
                    access_token,
                    json_data=payload,
                )
                results.extend(result.get("results", []))
            except HubSpotError as e:
                self.logger.error(
                    "hubspot_batch_create_failed",
                    batch_start=i,
                    batch_size=len(batch),
                    error=str(e),
                )

        self.logger.info(
            "hubspot_bulk_contacts_created",
            total_requested=len(contacts),
            total_created=len(results),
        )

        return results

    def map_lead_to_contact(self, lead: dict) -> dict:
        """Map a Scripe lead to HubSpot contact properties.

        Args:
            lead: Lead data from Scripe

        Returns:
            HubSpot contact properties
        """
        contact = {}

        # Basic info
        if lead.get("name"):
            # Try to split name into first/last
            parts = lead["name"].split(" ", 1)
            contact["firstname"] = parts[0]
            if len(parts) > 1:
                contact["lastname"] = parts[1]

        if lead.get("email"):
            contact["email"] = lead["email"]
        elif lead.get("contact_emails") and len(lead["contact_emails"]) > 0:
            contact["email"] = lead["contact_emails"][0].get("email")

        if lead.get("phone"):
            contact["phone"] = lead["phone"]
        elif lead.get("phones") and len(lead["phones"]) > 0:
            contact["phone"] = lead["phones"][0]

        # Company info
        if lead.get("company_name"):
            contact["company"] = lead["company_name"]

        if lead.get("website"):
            contact["website"] = lead["website"]

        # Location
        if lead.get("city"):
            contact["city"] = lead["city"]

        if lead.get("country"):
            contact["country"] = lead["country"]

        if lead.get("address"):
            contact["address"] = lead["address"]

        # Custom properties (if configured in HubSpot)
        if lead.get("category"):
            contact["scripe_category"] = lead["category"]

        if lead.get("quality_score"):
            contact["scripe_quality_score"] = str(lead["quality_score"])

        return contact

    def map_lead_to_company(self, lead: dict) -> dict:
        """Map a Scripe lead to HubSpot company properties.

        Args:
            lead: Lead data from Scripe

        Returns:
            HubSpot company properties
        """
        company = {}

        if lead.get("company_name") or lead.get("name"):
            company["name"] = lead.get("company_name") or lead.get("name")

        if lead.get("website"):
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(lead["website"])
            domain = parsed.netloc or lead["website"]
            if domain.startswith("www."):
                domain = domain[4:]
            company["domain"] = domain

        if lead.get("phone"):
            company["phone"] = lead["phone"]
        elif lead.get("phones") and len(lead["phones"]) > 0:
            company["phone"] = lead["phones"][0]

        if lead.get("city"):
            company["city"] = lead["city"]

        if lead.get("country"):
            company["country"] = lead["country"]

        if lead.get("address"):
            company["address"] = lead["address"]

        if lead.get("category"):
            company["industry"] = lead["category"]

        return company


# Singleton instance
hubspot_service = HubSpotService()
