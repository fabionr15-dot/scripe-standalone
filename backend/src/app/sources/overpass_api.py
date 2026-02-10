"""OpenStreetMap Overpass API connector for business data."""

from typing import Any

import httpx

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceConfig, SourceResult, SourceType

logger = get_logger(__name__)


# Mapping von Suchbegriffen zu OSM-Tags
# Erweitert für europäische Sprachen (DE, IT, FR, ES, EN)
CATEGORY_TO_OSM_TAGS: dict[str, list[str]] = {
    # Friseur / Hairdresser
    "friseur": ["shop=hairdresser", "shop=beauty"],
    "friseure": ["shop=hairdresser", "shop=beauty"],
    "parrucchiere": ["shop=hairdresser", "shop=beauty"],
    "parrucchieri": ["shop=hairdresser", "shop=beauty"],
    "coiffeur": ["shop=hairdresser", "shop=beauty"],
    "peluqueria": ["shop=hairdresser", "shop=beauty"],
    "hairdresser": ["shop=hairdresser", "shop=beauty"],

    # Restaurant
    "restaurant": ["amenity=restaurant"],
    "restaurants": ["amenity=restaurant"],
    "ristorante": ["amenity=restaurant"],
    "ristoranti": ["amenity=restaurant"],
    "restaurante": ["amenity=restaurant"],

    # Cafe
    "cafe": ["amenity=cafe"],
    "café": ["amenity=cafe"],
    "bar": ["amenity=bar", "amenity=cafe"],
    "caffè": ["amenity=cafe"],

    # Zahnarzt / Dentist
    "zahnarzt": ["amenity=dentist", "healthcare=dentist"],
    "zahnärzte": ["amenity=dentist", "healthcare=dentist"],
    "dentista": ["amenity=dentist", "healthcare=dentist"],
    "dentisti": ["amenity=dentist", "healthcare=dentist"],
    "dentiste": ["amenity=dentist", "healthcare=dentist"],
    "dentist": ["amenity=dentist", "healthcare=dentist"],

    # Arzt / Doctor
    "arzt": ["amenity=doctors", "healthcare=doctor"],
    "ärzte": ["amenity=doctors", "healthcare=doctor"],
    "medico": ["amenity=doctors", "healthcare=doctor"],
    "médecin": ["amenity=doctors", "healthcare=doctor"],
    "doctor": ["amenity=doctors", "healthcare=doctor"],

    # Apotheke / Pharmacy
    "apotheke": ["amenity=pharmacy"],
    "apotheken": ["amenity=pharmacy"],
    "farmacia": ["amenity=pharmacy"],
    "pharmacie": ["amenity=pharmacy"],
    "pharmacy": ["amenity=pharmacy"],

    # Anwalt / Lawyer
    "anwalt": ["office=lawyer"],
    "anwälte": ["office=lawyer"],
    "avvocato": ["office=lawyer"],
    "avvocati": ["office=lawyer"],
    "avocat": ["office=lawyer"],
    "abogado": ["office=lawyer"],
    "lawyer": ["office=lawyer"],

    # Hotel
    "hotel": ["tourism=hotel"],
    "hotels": ["tourism=hotel"],
    "albergo": ["tourism=hotel"],
    "alberghi": ["tourism=hotel"],

    # Bank
    "bank": ["amenity=bank"],
    "banca": ["amenity=bank"],
    "banque": ["amenity=bank"],
    "banco": ["amenity=bank"],

    # Supermarkt
    "supermarkt": ["shop=supermarket"],
    "supermercato": ["shop=supermarket"],
    "supermarché": ["shop=supermarket"],
    "supermercado": ["shop=supermarket"],
    "supermarket": ["shop=supermarket"],

    # Bäckerei / Bakery
    "bäckerei": ["shop=bakery"],
    "panetteria": ["shop=bakery"],
    "boulangerie": ["shop=bakery"],
    "panaderia": ["shop=bakery"],
    "bakery": ["shop=bakery"],

    # Metzger / Butcher
    "metzger": ["shop=butcher"],
    "metzgerei": ["shop=butcher"],
    "macelleria": ["shop=butcher"],
    "boucherie": ["shop=butcher"],
    "carniceria": ["shop=butcher"],
    "butcher": ["shop=butcher"],

    # Fitnessstudio / Gym
    "fitnessstudio": ["leisure=fitness_centre", "amenity=gym"],
    "fitness": ["leisure=fitness_centre", "amenity=gym"],
    "palestra": ["leisure=fitness_centre", "amenity=gym"],
    "gym": ["leisure=fitness_centre", "amenity=gym"],

    # Handwerker / Craftsmen
    "handwerker": ["craft=*"],
    "elektriker": ["craft=electrician"],
    "elettricista": ["craft=electrician"],
    "électricien": ["craft=electrician"],
    "electrician": ["craft=electrician"],
    "klempner": ["craft=plumber"],
    "idraulico": ["craft=plumber"],
    "plombier": ["craft=plumber"],
    "plumber": ["craft=plumber"],
    "tischler": ["craft=carpenter"],
    "falegname": ["craft=carpenter"],
    "menuisier": ["craft=carpenter"],
    "carpenter": ["craft=carpenter"],
    "schlosser": ["craft=locksmith"],
    "fabbro": ["craft=locksmith"],
    "serrurier": ["craft=locksmith"],
    "locksmith": ["craft=locksmith"],

    # Autowerkstatt / Car repair
    "autowerkstatt": ["shop=car_repair", "amenity=car_repair"],
    "kfz": ["shop=car_repair", "amenity=car_repair"],
    "autofficina": ["shop=car_repair", "amenity=car_repair"],
    "meccanico": ["shop=car_repair", "amenity=car_repair"],
    "garage": ["shop=car_repair", "amenity=car_repair"],
    "taller": ["shop=car_repair", "amenity=car_repair"],
    "car repair": ["shop=car_repair", "amenity=car_repair"],

    # Optiker / Optician
    "optiker": ["shop=optician"],
    "ottico": ["shop=optician"],
    "opticien": ["shop=optician"],
    "optician": ["shop=optician"],

    # Blumen / Florist
    "blumen": ["shop=florist"],
    "blumenladen": ["shop=florist"],
    "fiorista": ["shop=florist"],
    "fleuriste": ["shop=florist"],
    "florist": ["shop=florist"],

    # Immobilien / Real estate
    "immobilien": ["office=estate_agent"],
    "makler": ["office=estate_agent"],
    "immobiliare": ["office=estate_agent"],
    "agence immobilière": ["office=estate_agent"],
    "real estate": ["office=estate_agent"],

    # Versicherung / Insurance
    "versicherung": ["office=insurance"],
    "assicurazione": ["office=insurance"],
    "assurance": ["office=insurance"],
    "insurance": ["office=insurance"],

    # Steuerberater / Accountant
    "steuerberater": ["office=accountant", "office=tax_advisor"],
    "commercialista": ["office=accountant"],
    "comptable": ["office=accountant"],
    "accountant": ["office=accountant"],
}

# Fallback: Generische Suche
DEFAULT_OSM_TAGS = [
    "shop=*",
    "amenity=*",
    "office=*",
    "craft=*",
]


class OverpassConnector(BaseConnector):
    """OpenStreetMap Overpass API connector.

    Searches for businesses using the free Overpass API.
    Works for all countries worldwide with good coverage in Europe.
    """

    API_URL = "https://overpass-api.de/api/interpreter"

    config = SourceConfig(
        name="overpass_osm",
        source_type=SourceType.API,
        priority=2,  # After Google Places, before scrapers
        rate_limit=1.0,  # 1 request per second (be nice to public API)
        requires_api_key=False,
        supported_countries=["*"],  # All countries
        confidence_score=0.75,  # Community-generated data
        max_results_per_query=500,  # Can handle large queries
        timeout_seconds=120,  # Overpass can be slow for large areas
        requires_proxy=False,
    )

    def __init__(self):
        """Initialize Overpass connector."""
        super().__init__()
        self.logger = get_logger(__name__)

    def _get_osm_tags(self, query: str) -> list[str]:
        """Get OSM tags for a search query.

        Args:
            query: Search query (e.g., "friseur", "restaurant")

        Returns:
            List of OSM tag filters
        """
        query_lower = query.lower().strip()

        # Check for exact match first
        if query_lower in CATEGORY_TO_OSM_TAGS:
            return CATEGORY_TO_OSM_TAGS[query_lower]

        # Check for partial match
        for key, tags in CATEGORY_TO_OSM_TAGS.items():
            if key in query_lower or query_lower in key:
                return tags

        # Fallback: search in name tag
        return []

    def _build_query(
        self,
        query: str,
        city: str,
        country: str | None = None,
        limit: int = 100,
    ) -> str:
        """Build Overpass QL query.

        Args:
            query: Business type/category
            city: City name
            country: Country code (optional)
            limit: Max results

        Returns:
            Overpass QL query string
        """
        osm_tags = self._get_osm_tags(query)

        # Build area filter
        if country:
            # Map country codes to country names for OSM
            country_names = {
                "DE": "Deutschland",
                "AT": "Österreich",
                "IT": "Italia",
                "FR": "France",
                "ES": "España",
                "CH": "Schweiz",
                "NL": "Nederland",
                "BE": "België",
                "PL": "Polska",
                "CZ": "Česko",
            }
            country_name = country_names.get(country.upper(), country)
            area_filter = f'area["name"="{city}"]["admin_level"~"[468]"]->.searchArea;'
        else:
            area_filter = f'area["name"="{city}"]->.searchArea;'

        # Build tag filters
        if osm_tags:
            # Specific category search
            tag_queries = []
            for tag in osm_tags:
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    if value == "*":
                        tag_queries.append(f'  node["{key}"](area.searchArea);')
                        tag_queries.append(f'  way["{key}"](area.searchArea);')
                    else:
                        tag_queries.append(f'  node["{key}"="{value}"](area.searchArea);')
                        tag_queries.append(f'  way["{key}"="{value}"](area.searchArea);')
            tag_filter = "\n".join(tag_queries)
        else:
            # Generic name search
            tag_filter = f'''  node["name"~"{query}",i](area.searchArea);
  way["name"~"{query}",i](area.searchArea);'''

        # Build complete query
        overpass_query = f"""[out:json][timeout:60];
{area_filter}
(
{tag_filter}
);
out center {limit};"""

        return overpass_query

    def _parse_element(self, element: dict[str, Any], query: str) -> SourceResult | None:
        """Parse OSM element to SourceResult.

        Args:
            element: OSM element (node or way)
            query: Original search query

        Returns:
            SourceResult or None if invalid
        """
        tags = element.get("tags", {})

        # Must have a name
        name = tags.get("name")
        if not name:
            return None

        # Extract address components
        address_parts = []
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        if street:
            if housenumber:
                address_parts.append(f"{street} {housenumber}")
            else:
                address_parts.append(street)

        address_line = ", ".join(address_parts) if address_parts else None

        # Extract other data
        postal_code = tags.get("addr:postcode")
        city = tags.get("addr:city")
        region = tags.get("addr:state") or tags.get("addr:province")
        country = tags.get("addr:country")

        # Phone (try multiple tag variations)
        phone = (
            tags.get("phone") or
            tags.get("contact:phone") or
            tags.get("telephone")
        )

        # Website
        website = (
            tags.get("website") or
            tags.get("contact:website") or
            tags.get("url")
        )

        # Email
        email = tags.get("email") or tags.get("contact:email")

        # Category from OSM tags
        category = (
            tags.get("shop") or
            tags.get("amenity") or
            tags.get("office") or
            tags.get("craft") or
            tags.get("tourism") or
            tags.get("healthcare")
        )

        # Build source URL (link to OpenStreetMap)
        element_type = element.get("type", "node")
        element_id = element.get("id")
        source_url = f"https://www.openstreetmap.org/{element_type}/{element_id}"

        # Get coordinates for reference
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        return SourceResult(
            source_name=self.source_name,
            company_name=name,
            website=website,
            phone=phone,
            address_line=address_line,
            postal_code=postal_code,
            city=city,
            region=region,
            country=country,
            category=category,
            source_url=source_url,
            raw_data={
                "osm_id": element_id,
                "osm_type": element_type,
                "lat": lat,
                "lon": lon,
                "email": email,
                "tags": tags,
            },
        )

    async def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SourceResult]:
        """Search for businesses using Overpass API.

        Args:
            query: Business type (e.g., "friseur", "restaurant")
            region: City name
            limit: Maximum results
            **kwargs: Additional parameters (country)

        Returns:
            List of SourceResult
        """
        results: list[SourceResult] = []

        if not region:
            self.logger.warning("overpass_search_no_region", query=query)
            return results

        country = kwargs.get("country")

        try:
            # Build and execute query
            overpass_query = self._build_query(query, region, country, limit)

            self.logger.debug(
                "overpass_query",
                query=query,
                city=region,
                overpass_ql=overpass_query[:200],
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.API_URL,
                    data={"data": overpass_query},
                    timeout=self.config.timeout_seconds,
                    headers={
                        "User-Agent": "Scripe/1.0 (B2B Lead Generation)",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Parse elements
            elements = data.get("elements", [])

            for element in elements:
                result = self._parse_element(element, query)
                if result:
                    results.append(result)
                    if len(results) >= limit:
                        break

            self.log_search(f"{query} in {region}", len(results))
            self.mark_healthy()

        except httpx.TimeoutException as e:
            self.log_error("search", e)
            self.logger.warning("overpass_timeout", query=query, city=region)
        except httpx.HTTPStatusError as e:
            self.log_error("search", e)
            if e.response.status_code == 429:
                self.mark_unhealthy("rate_limited")
            elif e.response.status_code >= 500:
                self.mark_unhealthy("server_error")
        except Exception as e:
            self.log_error("search", e)

        return results

    async def enrich(self, company_data: dict[str, Any]) -> SourceResult | None:
        """Enrich company data using OSM.

        For Overpass, we search by name + city to find additional details.

        Args:
            company_data: Existing company data

        Returns:
            Enriched SourceResult or None
        """
        name = company_data.get("company_name")
        city = company_data.get("city")

        if not name or not city:
            return None

        # Search by exact name
        results = await self.search(
            query=name,
            region=city,
            limit=5,
        )

        # Return first match (if any)
        if results:
            # Try to find exact name match
            for result in results:
                if result.company_name.lower() == name.lower():
                    return result
            # Otherwise return first result
            return results[0]

        return None

    async def health_check(self) -> bool:
        """Check if Overpass API is available.

        Returns:
            True if API is responding
        """
        try:
            async with httpx.AsyncClient() as client:
                # Simple test query
                response = await client.get(
                    "https://overpass-api.de/api/status",
                    timeout=10,
                )
                return response.status_code == 200
        except Exception:
            return False
