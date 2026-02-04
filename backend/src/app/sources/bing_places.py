"""Bing Maps Places API connector."""

from typing import Any

import httpx

from app.logging_config import get_logger
from app.settings import settings
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


class BingPlacesConnector(BaseConnector):
    """Bing Maps Local Search API connector for business data.

    Provides business search as a backup/complement to Google Places.
    See: https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/local-search
    """

    API_BASE_URL = "https://dev.virtualearth.net/REST/v1/LocalSearch"

    # Source configuration
    config = SourceConfig(
        name="bing_places",
        source_type=SourceType.API,
        priority=2,  # Second priority after Google
        rate_limit=5.0,  # Bing rate limits
        requires_api_key=True,
        api_key_env_var="BING_MAPS_API_KEY",
        supported_countries=["*"],  # Global coverage
        enabled=True,
        confidence_score=0.85,  # Slightly lower than Google
        max_results_per_query=25,  # Bing returns max 25 results
        timeout_seconds=30,
        retry_count=3,
        requires_proxy=False,
    )

    def __init__(self, api_key: str | None = None):
        """Initialize Bing Places connector.

        Args:
            api_key: Bing Maps API key (defaults to settings)
        """
        super().__init__()
        self.api_key = api_key or getattr(settings, "bing_maps_api_key", None)

        if not self.api_key:
            logger.warning("bing_maps_api_key_not_configured")
            self.config.enabled = False

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search for businesses using Bing Local Search API.

        Args:
            query: Search query (e.g., "dentist", "restaurant")
            region: Geographic region (city, region)
            limit: Maximum results (max 25)
            **kwargs: Additional parameters (language, userLocation)

        Returns:
            List of source results
        """
        if not self.api_key:
            logger.error("bing_search_skipped_no_api_key")
            return []

        results = []

        try:
            async with httpx.AsyncClient() as client:
                params: dict[str, Any] = {
                    "query": query,
                    "key": self.api_key,
                    "maxResults": min(limit, 25),
                }

                # Add location context if provided
                if region:
                    # Bing expects userLocation as "lat,lng" or we can use the query
                    params["query"] = f"{query} in {region}"

                # Add optional country filter
                country = kwargs.get("country")
                if country:
                    params["userRegion"] = country

                # Add optional language
                language = kwargs.get("language", "it-IT")
                params["culture"] = language

                response = await client.get(
                    self.API_BASE_URL,
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()

                # Check for errors
                status_code = data.get("statusCode", 0)
                if status_code != 200:
                    logger.warning(
                        "bing_api_error",
                        status_code=status_code,
                        status_description=data.get("statusDescription"),
                    )
                    return []

                # Parse resource sets
                resource_sets = data.get("resourceSets", [])
                if not resource_sets:
                    return []

                resources = resource_sets[0].get("resources", [])
                for resource in resources[:limit]:
                    result = self._parse_resource(resource)
                    if result:
                        results.append(result)

                self.log_search(f"{query} in {region}" if region else query, len(results))

        except httpx.HTTPError as e:
            self.log_error("search", e)
        except Exception as e:
            self.log_error("search", e)

        return results

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data using Bing search.

        Args:
            company_data: Partial company data (should include name and location)

        Returns:
            Enriched source result or None
        """
        if not self.api_key:
            return None

        name = company_data.get("company_name")
        city = company_data.get("city")

        if not name:
            return None

        # Search for the specific business
        query = f"{name} {city}" if city else name
        results = await self.search(query, limit=5)

        # Try to find a match
        if results:
            # Return first result (could add fuzzy matching later)
            return results[0]

        return None

    def _parse_resource(self, resource: dict[str, Any]) -> SourceResult | None:
        """Parse a resource from Bing API response.

        Args:
            resource: Resource data from API

        Returns:
            Source result or None
        """
        name = resource.get("name")
        if not name:
            return None

        # Extract address from Address object
        address_obj = resource.get("Address", {})
        address_line = address_obj.get("addressLine")
        city = address_obj.get("locality")
        region = address_obj.get("adminDistrict")  # State/Province
        postal_code = address_obj.get("postalCode")
        country = address_obj.get("countryRegion")

        # Full formatted address
        formatted_address = address_obj.get("formattedAddress", "")

        # Phone number
        phone = resource.get("PhoneNumber")

        # Website
        website = resource.get("Website")

        # Categories
        entity_type = resource.get("entityType")

        # Source URL (Bing Maps link)
        point = resource.get("point", {})
        coordinates = point.get("coordinates", [])
        source_url = None
        if len(coordinates) >= 2:
            lat, lng = coordinates[0], coordinates[1]
            source_url = f"https://www.bing.com/maps?cp={lat}~{lng}&lvl=16"

        return SourceResult(
            source_name=self.source_name,
            company_name=name,
            website=website,
            phone=phone,
            address_line=address_line or formatted_address,
            postal_code=postal_code,
            city=city,
            region=region,
            country=country,
            category=entity_type,
            source_url=source_url,
            raw_data=resource,
        )

    async def health_check(self) -> bool:
        """Check if Bing Maps API is accessible.

        Returns:
            True if API is healthy and accessible
        """
        if not self.api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "query": "test",
                    "key": self.api_key,
                    "maxResults": 1,
                }
                response = await client.get(
                    self.API_BASE_URL,
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                data = response.json()
                is_healthy = data.get("statusCode") == 200
                if is_healthy:
                    self.mark_healthy()
                else:
                    self.mark_unhealthy(f"API status: {data.get('statusCode')}")
                return is_healthy
        except Exception as e:
            self.mark_unhealthy(str(e))
            return False
