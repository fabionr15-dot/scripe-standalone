"""Google Places API (New) connector."""

from typing import Any

import httpx

from app.logging_config import get_logger
from app.settings import settings
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class PlacesConnector(BaseConnector):
    """Google Places API (New) connector for business data.

    Uses the new Places API with searchText endpoint.
    See: https://developers.google.com/maps/documentation/places/web-service/text-search
    """

    API_BASE_URL = "https://places.googleapis.com/v1/places"

    # Source configuration
    config = SourceConfig(
        name="google_places",
        source_type=SourceType.API,
        priority=1,  # Highest priority - official API
        rate_limit=10.0,  # Google allows ~10 QPS
        requires_api_key=True,
        api_key_env_var="GOOGLE_PLACES_API_KEY",
        supported_countries=["*"],  # Global coverage
        enabled=True,
        confidence_score=0.9,  # High confidence - official source
        max_results_per_query=60,  # API returns max 20 per request, paginated
        timeout_seconds=30,
        retry_count=3,
        requires_proxy=False,
    )

    def __init__(self, api_key: str | None = None):
        """Initialize Places connector.

        Args:
            api_key: Google Places API key (defaults to settings)
        """
        super().__init__()
        self.api_key = api_key or settings.google_places_api_key

        if not self.api_key:
            logger.warning("google_places_api_key_not_configured")
            self.config.enabled = False

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search for businesses using Places API (New) Text Search.

        Args:
            query: Search query (e.g., "dentist", "restaurant")
            region: Geographic region (city, region)
            limit: Maximum results
            **kwargs: Additional parameters (language, etc.)

        Returns:
            List of source results
        """
        if not self.api_key:
            logger.error("places_search_skipped_no_api_key")
            return []

        # Construct full query with region
        full_query = f"{query} in {region}" if region else query

        results = []

        try:
            async with httpx.AsyncClient() as client:
                # Places API (New) Text Search endpoint
                url = f"{self.API_BASE_URL}:searchText"

                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": (
                        "places.displayName,places.formattedAddress,"
                        "places.internationalPhoneNumber,places.websiteUri,"
                        "places.types,places.addressComponents,places.id,"
                        "places.location,nextPageToken"
                    ),
                }

                language = kwargs.get("language", "it")

                body = {
                    "textQuery": full_query,
                    "languageCode": language,
                    "maxResultCount": min(limit, 20),  # API max is 20 per request
                }

                # First page
                response = await client.post(url, json=body, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                # Parse results
                places = data.get("places", [])
                for place in places:
                    result = self._parse_place(place)
                    if result:
                        results.append(result)

                # Handle pagination with nextPageToken
                page_token = data.get("nextPageToken")
                while page_token and len(results) < limit:
                    body["pageToken"] = page_token
                    body.pop("textQuery", None)  # Not needed with pageToken

                    response = await client.post(url, json=body, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()

                    places = data.get("places", [])
                    for place in places:
                        result = self._parse_place(place)
                        if result:
                            results.append(result)

                    page_token = data.get("nextPageToken")

                self.log_search(full_query, len(results))

        except httpx.HTTPError as e:
            self.log_error("search", e)
        except Exception as e:
            self.log_error("search", e)

        return results[:limit]

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data using Places Details API.

        Args:
            company_data: Partial company data (must include place_id or name+location)

        Returns:
            Enriched source result or None
        """
        if not self.api_key:
            return None

        place_id = company_data.get("place_id")
        if not place_id:
            logger.debug("places_enrich_no_place_id")
            return None

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.API_BASE_URL}/{place_id}"
                headers = {
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": (
                        "displayName,formattedAddress,internationalPhoneNumber,"
                        "websiteUri,types,addressComponents,id,location"
                    ),
                }

                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                place = response.json()
                return self._parse_place(place)

        except Exception as e:
            self.log_error("enrich", e)
            return None

    def _parse_place(self, place: dict[str, Any]) -> SourceResult | None:
        """Parse a place result from Places API (New).

        Args:
            place: Place data from API

        Returns:
            Source result or None
        """
        # Get display name
        display_name = place.get("displayName", {})
        name = display_name.get("text") if isinstance(display_name, dict) else display_name
        if not name:
            return None

        # Extract fields
        address = place.get("formattedAddress", "")
        website = place.get("websiteUri")
        phone = place.get("internationalPhoneNumber")

        # Parse address components
        city = None
        region = None
        postal_code = None
        country = None

        address_components = place.get("addressComponents", [])
        for component in address_components:
            types = component.get("types", [])
            if "locality" in types:
                city = component.get("longText")
            elif "administrative_area_level_1" in types:
                region = component.get("longText")
            elif "postal_code" in types:
                postal_code = component.get("longText")
            elif "country" in types:
                country = component.get("shortText")

        # Category from types
        types = place.get("types", [])
        category = types[0] if types else None

        # Source URL
        place_id = place.get("id")
        source_url = (
            f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
        )

        return SourceResult(
            source_name=self.source_name,
            company_name=name,
            website=website,
            phone=phone,
            address_line=address,
            postal_code=postal_code,
            city=city,
            region=region,
            country=country,
            category=category,
            source_url=source_url,
            raw_data=place,
        )

    async def health_check(self) -> bool:
        """Check if Google Places API (New) is accessible.

        Returns:
            True if API is healthy and accessible
        """
        if not self.api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.API_BASE_URL}:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": "places.displayName",
                }
                body = {
                    "textQuery": "test",
                    "maxResultCount": 1,
                }

                response = await client.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=self.config.timeout_seconds,
                )

                # 200 means API is working (even with empty results)
                is_healthy = response.status_code == 200
                if is_healthy:
                    self.mark_healthy()
                else:
                    error_data = response.json() if response.content else {}
                    self.mark_unhealthy(
                        f"API status: {response.status_code} - {error_data.get('error', {}).get('message', 'Unknown')}"
                    )
                return is_healthy
        except Exception as e:
            self.mark_unhealthy(str(e))
            return False
