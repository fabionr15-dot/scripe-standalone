"""Google Places API connector."""

from typing import Any

import httpx

from app.logging_config import get_logger
from app.settings import settings
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class PlacesConnector(BaseConnector):
    """Google Places API connector for business data.

    Note: Requires Google Places API key and respects API ToS.
    See: https://developers.google.com/maps/documentation/places/web-service/usage-and-billing
    """

    API_BASE_URL = "https://maps.googleapis.com/maps/api/place"

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
        max_results_per_query=60,  # API returns max 60 with pagination
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
        """Search for businesses using Places API Text Search.

        Args:
            query: Search query (e.g., "dentist", "restaurant")
            region: Geographic region (city, region)
            limit: Maximum results
            **kwargs: Additional parameters (language, radius, etc.)

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
                # Places API Text Search endpoint
                url = f"{self.API_BASE_URL}/textsearch/json"
                params = {
                    "query": full_query,
                    "key": self.api_key,
                    "language": kwargs.get("language", "it"),
                }

                # Add optional location bias
                if "location" in kwargs and "radius" in kwargs:
                    params["location"] = kwargs["location"]
                    params["radius"] = kwargs["radius"]

                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(
                        "places_api_error",
                        status=data.get("status"),
                        error_message=data.get("error_message"),
                    )
                    return []

                # Parse results
                places = data.get("results", [])
                for place in places[:limit]:
                    result = self._parse_place(place)
                    if result:
                        results.append(result)

                # Handle pagination if needed (next_page_token)
                # Note: Implementing pagination requires managing rate limits and delays

                self.log_search(full_query, len(results))

        except httpx.HTTPError as e:
            self.log_error("search", e)
        except Exception as e:
            self.log_error("search", e)

        return results

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
            # Could implement Find Place to get place_id first
            logger.debug("places_enrich_no_place_id")
            return None

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.API_BASE_URL}/details/json"
                params = {
                    "place_id": place_id,
                    "key": self.api_key,
                    "fields": "name,formatted_address,formatted_phone_number,website,types,geometry",
                }

                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "OK":
                    logger.warning("places_details_error", status=data.get("status"))
                    return None

                place = data.get("result", {})
                return self._parse_place(place)

        except Exception as e:
            self.log_error("enrich", e)
            return None

    def _parse_place(self, place: dict[str, Any]) -> SourceResult | None:
        """Parse a place result from Places API.

        Args:
            place: Place data from API

        Returns:
            Source result or None
        """
        name = place.get("name")
        if not name:
            return None

        # Extract address components
        address = place.get("formatted_address", "")
        website = place.get("website")
        phone = place.get("formatted_phone_number") or place.get("international_phone_number")

        # Parse address (simplified - could be more sophisticated)
        city = None
        region = None
        postal_code = None
        country = None

        address_components = place.get("address_components", [])
        for component in address_components:
            types = component.get("types", [])
            if "locality" in types:
                city = component.get("long_name")
            elif "administrative_area_level_1" in types:
                region = component.get("long_name")
            elif "postal_code" in types:
                postal_code = component.get("long_name")
            elif "country" in types:
                country = component.get("short_name")

        # Category from types
        types = place.get("types", [])
        category = types[0] if types else None

        # Source URL
        place_id = place.get("place_id")
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
        """Check if Google Places API is accessible.

        Returns:
            True if API is healthy and accessible
        """
        if not self.api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                # Simple test query
                url = f"{self.API_BASE_URL}/textsearch/json"
                params = {
                    "query": "test",
                    "key": self.api_key,
                }
                response = await client.get(
                    url,
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                data = response.json()
                # OK or ZERO_RESULTS both mean API is working
                is_healthy = data.get("status") in ["OK", "ZERO_RESULTS"]
                if is_healthy:
                    self.mark_healthy()
                else:
                    self.mark_unhealthy(f"API status: {data.get('status')}")
                return is_healthy
        except Exception as e:
            self.mark_unhealthy(str(e))
            return False
