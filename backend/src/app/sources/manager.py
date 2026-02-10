"""Source Manager - Orchestrates multiple data sources for lead generation.

CRITICAL: This manager MUST deliver the exact number of leads requested.
If customer orders 100 leads → deliver 100
If customer orders 1,000 leads → deliver 1,000
If customer orders 30,000 leads → deliver 30,000

Time is not a constraint - quality over speed.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.logging_config import get_logger
from app.sources.base import BaseConnector, SourceResult, SourceType

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CITIES PER COUNTRY - Used to iterate when searching for large quantities
# ─────────────────────────────────────────────────────────────────────────────
COUNTRY_CITIES: dict[str, list[str]] = {
    "IT": [
        # Major cities (population > 500k)
        "Milano", "Roma", "Napoli", "Torino", "Palermo", "Genova", "Bologna",
        "Firenze", "Bari", "Catania", "Venezia", "Verona", "Messina", "Padova",
        # Large cities (population > 200k)
        "Trieste", "Brescia", "Parma", "Taranto", "Prato", "Modena", "Reggio Calabria",
        "Reggio Emilia", "Perugia", "Ravenna", "Livorno", "Cagliari", "Foggia",
        "Rimini", "Salerno", "Ferrara", "Sassari", "Latina", "Giugliano",
        # Medium cities (population > 100k)
        "Monza", "Siracusa", "Pescara", "Bergamo", "Forlì", "Trento", "Vicenza",
        "Terni", "Bolzano", "Novara", "Piacenza", "Ancona", "Andria", "Arezzo",
        "Udine", "Cesena", "Lecce", "Pesaro", "Barletta", "Alessandria",
        "La Spezia", "Pistoia", "Pisa", "Catanzaro", "Lucca", "Como",
        # Smaller but important cities
        "Grosseto", "Varese", "Caserta", "Asti", "Ragusa", "Cremona", "Cosenza",
        "Massa", "Potenza", "Trapani", "Viterbo", "Crotone", "Cuneo", "Benevento",
        "Avellino", "Matera", "Agrigento", "Teramo", "Pordenone", "Savona",
    ],
    "DE": [
        # Major cities
        "Berlin", "Hamburg", "München", "Köln", "Frankfurt am Main", "Stuttgart",
        "Düsseldorf", "Leipzig", "Dortmund", "Essen", "Bremen", "Dresden",
        "Hannover", "Nürnberg", "Duisburg", "Bochum", "Wuppertal", "Bielefeld",
        # Large cities
        "Bonn", "Münster", "Mannheim", "Karlsruhe", "Augsburg", "Wiesbaden",
        "Mönchengladbach", "Gelsenkirchen", "Aachen", "Braunschweig", "Kiel",
        "Chemnitz", "Halle", "Magdeburg", "Freiburg", "Krefeld", "Mainz",
        "Lübeck", "Erfurt", "Oberhausen", "Rostock", "Kassel", "Hagen",
        # Medium cities
        "Potsdam", "Saarbrücken", "Hamm", "Ludwigshafen", "Oldenburg", "Mülheim",
        "Osnabrück", "Leverkusen", "Heidelberg", "Solingen", "Darmstadt",
        "Herne", "Neuss", "Regensburg", "Paderborn", "Ingolstadt", "Offenbach",
        "Würzburg", "Fürth", "Ulm", "Heilbronn", "Pforzheim", "Wolfsburg",
        "Göttingen", "Bottrop", "Reutlingen", "Koblenz", "Bremerhaven",
        "Remscheid", "Bergisch Gladbach", "Trier", "Jena", "Erlangen",
    ],
    "AT": [
        # Major cities
        "Wien", "Graz", "Linz", "Salzburg", "Innsbruck",
        # Other cities
        "Klagenfurt", "Villach", "Wels", "Sankt Pölten", "Dornbirn",
        "Wiener Neustadt", "Steyr", "Feldkirch", "Bregenz", "Leonding",
        "Klosterneuburg", "Baden", "Leoben", "Traun", "Krems an der Donau",
        "Amstetten", "Lustenau", "Kapfenberg", "Mödling", "Hallein",
        "Braunau am Inn", "Kufstein", "Schwechat", "Traiskirchen", "Tulln",
    ],
    "CH": [
        # Major cities (German)
        "Zürich", "Genf", "Basel", "Bern", "Lausanne", "Winterthur",
        # Other cities
        "Luzern", "St. Gallen", "Lugano", "Biel", "Thun", "Köniz",
        "La Chaux-de-Fonds", "Fribourg", "Schaffhausen", "Chur", "Neuchâtel",
        "Vernier", "Uster", "Sion", "Lancy", "Emmen", "Yverdon-les-Bains",
        "Zug", "Kriens", "Rapperswil-Jona", "Dübendorf", "Montreux",
    ],
    "FR": [
        # Major cities
        "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg",
        "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Saint-Étienne",
        "Le Havre", "Toulon", "Grenoble", "Dijon", "Angers", "Nîmes", "Villeurbanne",
        # Large cities
        "Clermont-Ferrand", "Le Mans", "Aix-en-Provence", "Brest", "Tours",
        "Amiens", "Limoges", "Annecy", "Perpignan", "Boulogne-Billancourt",
        "Metz", "Besançon", "Orléans", "Rouen", "Mulhouse", "Caen", "Nancy",
        "Saint-Denis", "Argenteuil", "Montreuil", "Roubaix", "Tourcoing",
    ],
    "ES": [
        # Major cities
        "Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga",
        "Murcia", "Palma", "Las Palmas", "Bilbao", "Alicante", "Córdoba",
        "Valladolid", "Vigo", "Gijón", "L'Hospitalet", "A Coruña", "Vitoria",
        # Large cities
        "Granada", "Elche", "Oviedo", "Badalona", "Cartagena", "Terrassa",
        "Jerez", "Sabadell", "Móstoles", "Santa Cruz", "Pamplona", "Almería",
        "Alcalá", "Fuenlabrada", "Leganés", "San Sebastián", "Getafe", "Burgos",
        "Albacete", "Santander", "Castellón", "Alcorcón", "San Cristóbal",
    ],
    # Default for countries not specifically listed
    "default": [
        "Capital", "City1", "City2", "City3", "City4",
    ],
}


@dataclass
class SearchCriteria:
    """Search criteria for lead generation."""
    query: str  # Main search query (category, keywords)
    country: str = "IT"  # Primary country (for backward compatibility)
    countries: list[str] | None = None  # All countries for multi-country search
    regions: list[str] | None = None
    cities: list[str] | None = None
    keywords_include: list[str] | None = None
    keywords_exclude: list[str] | None = None
    target_count: int = 100
    min_sources: int = 1  # Minimum sources to query
    max_sources: int | None = None  # None = all available

    # Advanced filters
    technologies: list[str] | None = None  # SAP, Salesforce, etc.
    company_size: str | None = None  # small, medium, large, enterprise
    employee_count_min: int | None = None
    employee_count_max: int | None = None


@dataclass
class SearchProgress:
    """Progress tracking for search operations."""
    total_sources: int
    completed_sources: int
    results_found: int
    target_count: int
    current_source: str | None = None
    current_city: str | None = None
    cities_searched: int = 0
    total_cities: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def percent_complete(self) -> int:
        """Get completion percentage based on results found vs target."""
        if self.target_count == 0:
            return 100
        return min(100, int((self.results_found / self.target_count) * 100))

    @property
    def target_reached(self) -> bool:
        """Check if target count is reached."""
        return self.results_found >= self.target_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_sources": self.total_sources,
            "completed_sources": self.completed_sources,
            "results_found": self.results_found,
            "target_count": self.target_count,
            "current_source": self.current_source,
            "current_city": self.current_city,
            "cities_searched": self.cities_searched,
            "total_cities": self.total_cities,
            "percent_complete": self.percent_complete,
            "target_reached": self.target_reached,
            "errors": self.errors,
        }


class SourceManager:
    """Orchestrates multiple data sources for lead generation.

    Supports:
    - Parallel search across multiple sources
    - Cascade search (stop when target reached)
    - Priority-based source ordering
    - Country-specific source filtering
    - Health monitoring
    """

    def __init__(self):
        """Initialize source manager."""
        self._sources: dict[str, BaseConnector] = {}
        self.logger = get_logger(__name__)

    def register(self, source: BaseConnector) -> None:
        """Register a data source.

        Args:
            source: Source connector to register
        """
        self._sources[source.source_name] = source
        self.logger.info(
            "source_registered",
            source=source.source_name,
            type=source.config.source_type.value,
            priority=source.config.priority,
        )

    def unregister(self, source_name: str) -> None:
        """Unregister a data source.

        Args:
            source_name: Name of source to remove
        """
        if source_name in self._sources:
            del self._sources[source_name]
            self.logger.info("source_unregistered", source=source_name)

    def get_source(self, name: str) -> BaseConnector | None:
        """Get a specific source by name.

        Args:
            name: Source name

        Returns:
            Source connector or None
        """
        return self._sources.get(name)

    def list_sources(self) -> list[dict[str, Any]]:
        """List all registered sources with their status.

        Returns:
            List of source info dicts
        """
        return [
            {
                "name": source.source_name,
                "type": source.config.source_type.value,
                "priority": source.config.priority,
                "enabled": source.is_enabled,
                "countries": source.config.supported_countries,
                "requires_api_key": source.config.requires_api_key,
                "confidence_score": source.config.confidence_score,
            }
            for source in sorted(
                self._sources.values(),
                key=lambda s: s.config.priority
            )
        ]

    def get_sources_for_country(self, country: str) -> list[BaseConnector]:
        """Get sources that support a specific country.

        Args:
            country: Country code

        Returns:
            List of compatible sources, ordered by priority
        """
        compatible = [
            source for source in self._sources.values()
            if source.is_enabled and source.supports_country(country)
        ]
        return sorted(compatible, key=lambda s: s.config.priority)

    async def search_all(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[Callable] = None,
    ) -> list[SourceResult]:
        """Search all compatible sources in parallel.

        Args:
            criteria: Search criteria
            progress_callback: Optional callback for progress updates

        Returns:
            Combined results from all sources
        """
        sources = self.get_sources_for_country(criteria.country)

        if criteria.max_sources:
            sources = sources[:criteria.max_sources]

        if not sources:
            self.logger.warning("no_sources_available", country=criteria.country)
            return []

        progress = SearchProgress(
            total_sources=len(sources),
            completed_sources=0,
            results_found=0,
            target_count=criteria.target_count,
        )

        self.logger.info(
            "search_all_started",
            query=criteria.query,
            country=criteria.country,
            sources=[s.source_name for s in sources],
        )

        # Create tasks for parallel execution
        tasks = []
        for source in sources:
            task = self._search_source(source, criteria, progress, progress_callback)
            tasks.append(task)

        # Execute all in parallel
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_results: list[SourceResult] = []
        for i, results in enumerate(results_lists):
            if isinstance(results, Exception):
                self.logger.error(
                    "source_search_failed",
                    source=sources[i].source_name,
                    error=str(results),
                )
                continue
            if results:
                all_results.extend(results)

        self.logger.info(
            "search_all_completed",
            total_results=len(all_results),
            sources_queried=len(sources),
        )

        return all_results

    async def search_cascade(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[Callable] = None,
    ) -> list[SourceResult]:
        """Search sources across ALL cities in ALL countries until target is reached.

        CRITICAL: This method MUST deliver the exact number of leads requested.
        - If customer orders 100 → deliver 100
        - If customer orders 1,000 → deliver 1,000
        - If customer orders 30,000 → deliver 30,000

        For multi-country searches, iterates through all countries and all cities
        within each country until the target count is reached.

        Args:
            criteria: Search criteria
            progress_callback: Optional callback for progress updates

        Returns:
            Results up to target count
        """
        # Get all countries to search (multi-country support)
        countries_to_search = self._get_countries_to_search(criteria)

        # Collect all cities from all countries
        all_cities_with_country: list[tuple[str, str]] = []  # (city, country_code)
        for country_code in countries_to_search:
            country_cities = self._get_cities_for_country(country_code, criteria)
            for city in country_cities:
                all_cities_with_country.append((city, country_code))

        if not all_cities_with_country:
            self.logger.warning("no_cities_available", countries=countries_to_search)
            return []

        # Get sources for all countries (deduplicated)
        all_sources: dict[str, list] = {}  # country -> sources
        for country_code in countries_to_search:
            sources = self.get_sources_for_country(country_code)
            if sources:
                all_sources[country_code] = sources

        if not all_sources:
            self.logger.warning("no_sources_available", countries=countries_to_search)
            return []

        # Calculate total source count for progress
        unique_source_names = set()
        for sources in all_sources.values():
            for s in sources:
                unique_source_names.add(s.source_name)

        progress = SearchProgress(
            total_sources=len(unique_source_names),
            completed_sources=0,
            results_found=0,
            target_count=criteria.target_count,
            total_cities=len(all_cities_with_country),
        )

        self.logger.info(
            "search_cascade_started",
            query=criteria.query,
            countries=countries_to_search,
            target=criteria.target_count,
            cities_count=len(all_cities_with_country),
            sources_per_country={k: [s.source_name for s in v] for k, v in all_sources.items()},
        )

        all_results: list[SourceResult] = []
        seen_companies: set[str] = set()  # Deduplicate by company name

        # MAIN LOOP: Iterate through cities in ALL countries until target reached
        for city_index, (city, country_code) in enumerate(all_cities_with_country):
            if progress.target_reached:
                self.logger.info(
                    "target_reached",
                    results=progress.results_found,
                    target=criteria.target_count,
                    city=city,
                    country=country_code,
                )
                break

            progress.current_city = f"{city} ({country_code})"
            progress.cities_searched = city_index + 1

            self.logger.debug(
                "searching_city",
                city=city,
                country=country_code,
                city_index=city_index + 1,
                total_cities=len(all_cities_with_country),
                results_so_far=len(all_results),
            )

            # Get sources for this country
            sources = all_sources.get(country_code, [])
            if not sources:
                continue

            # Search all sources for this city
            for source in sources:
                if progress.target_reached:
                    break

                # How many more do we need?
                remaining = criteria.target_count - len(all_results)

                results = await self._search_source_for_city(
                    source=source,
                    query=criteria.query,
                    city=city,
                    country=country_code,
                    limit=min(remaining * 2, 100),  # Get up to 2x what we need, max 100 per source/city
                    progress=progress,
                    progress_callback=progress_callback,
                )

                # Add results, deduplicating by company name
                for result in results:
                    company_key = result.company_name.lower().strip()
                    if company_key not in seen_companies:
                        seen_companies.add(company_key)
                        all_results.append(result)

                progress.results_found = len(all_results)

                if progress_callback:
                    progress_callback(progress)

            # Log progress after each city
            if (city_index + 1) % 5 == 0:
                self.logger.info(
                    "search_progress",
                    cities_searched=city_index + 1,
                    total_cities=len(all_cities_with_country),
                    results_found=len(all_results),
                    target=criteria.target_count,
                    percent_complete=progress.percent_complete,
                )

        self.logger.info(
            "search_cascade_completed",
            total_results=len(all_results),
            cities_searched=progress.cities_searched,
            target=criteria.target_count,
            target_reached=progress.target_reached,
        )

        return all_results[:criteria.target_count]

    def _get_countries_to_search(self, criteria: SearchCriteria) -> list[str]:
        """Get list of countries to search.

        Supports multi-country searches via the 'countries' field.
        Falls back to single 'country' field for backward compatibility.

        Args:
            criteria: Search criteria

        Returns:
            List of country codes to search
        """
        # Multi-country search
        if criteria.countries and len(criteria.countries) > 0:
            return criteria.countries

        # Single country (backward compatibility)
        return [criteria.country.upper()]

    def _get_cities_for_country(
        self, country_code: str, criteria: SearchCriteria
    ) -> list[str]:
        """Get list of cities for a specific country.

        If user specified cities/regions for this country, use those.
        Otherwise, return all cities for the country.

        Args:
            country_code: Country code (e.g., "IT", "DE")
            criteria: Search criteria (for user-specified cities)

        Returns:
            List of cities to search in this country
        """
        country_upper = country_code.upper()

        # User specified specific cities (use for all countries)
        if criteria.cities and len(criteria.cities) > 0:
            return criteria.cities

        # User specified specific regions (treat as cities)
        if criteria.regions and len(criteria.regions) > 0:
            # Filter out region entries that are country markers
            actual_regions = [
                r for r in criteria.regions
                if not r.startswith("country:")
            ]
            if actual_regions:
                return actual_regions

        # Get all cities for this country
        if country_upper in COUNTRY_CITIES:
            return COUNTRY_CITIES[country_upper]

        # Fallback to default cities
        self.logger.warning(
            "no_cities_for_country",
            country=country_upper,
            using_default=True,
        )
        return COUNTRY_CITIES.get("default", [""])

    def _get_cities_for_criteria(self, criteria: SearchCriteria) -> list[str]:
        """Get list of cities to search based on criteria.

        DEPRECATED: Use _get_cities_for_country for multi-country support.
        Kept for backward compatibility with search_all().

        Args:
            criteria: Search criteria

        Returns:
            List of cities to search
        """
        return self._get_cities_for_country(criteria.country, criteria)

    async def _search_source_for_city(
        self,
        source: BaseConnector,
        query: str,
        city: str,
        country: str,
        limit: int,
        progress: SearchProgress,
        progress_callback: Optional[Callable] = None,
    ) -> list[SourceResult]:
        """Search a single source for a specific city.

        Args:
            source: Source to search
            query: Search query
            city: City to search
            country: Country code
            limit: Max results
            progress: Progress tracker
            progress_callback: Optional callback

        Returns:
            Results from source
        """
        progress.current_source = source.source_name

        if progress_callback:
            progress_callback(progress)

        try:
            results = await source.search(
                query=query,
                region=city,
                limit=limit,
            )

            self.logger.debug(
                "source_search_result",
                source=source.source_name,
                city=city,
                results=len(results),
            )

            source.mark_healthy()
            return results

        except Exception as e:
            source.mark_unhealthy(str(e))
            source.log_error("search", e)
            progress.errors.append(f"{source.source_name} ({city}): {str(e)}")
            return []

    async def _search_source(
        self,
        source: BaseConnector,
        criteria: SearchCriteria,
        progress: SearchProgress,
        progress_callback: Optional[Callable] = None,
        limit: int | None = None,
    ) -> list[SourceResult]:
        """Search a single source across ALL cities.

        This is used by search_all() for parallel search.
        It iterates through all cities until the limit is reached.

        Args:
            source: Source to search
            criteria: Search criteria
            progress: Progress tracker
            progress_callback: Optional callback
            limit: Override result limit

        Returns:
            Results from source
        """
        progress.current_source = source.source_name

        if progress_callback:
            progress_callback(progress)

        all_results: list[SourceResult] = []
        cities = self._get_cities_for_criteria(criteria)
        max_results = limit or source.config.max_results_per_query

        try:
            for city in cities:
                if len(all_results) >= max_results:
                    break

                remaining = max_results - len(all_results)

                results = await source.search(
                    query=criteria.query,
                    region=city,
                    limit=min(remaining, 100),
                )

                if results:
                    all_results.extend(results)

            source.mark_healthy()
            return all_results[:max_results]

        except Exception as e:
            source.mark_unhealthy(str(e))
            source.log_error("search", e)
            progress.errors.append(f"{source.source_name}: {str(e)}")
            return all_results  # Return what we got so far

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all sources.

        Returns:
            Dict of source_name -> is_healthy
        """
        results = {}
        for name, source in self._sources.items():
            try:
                results[name] = await source.health_check()
            except Exception:
                results[name] = False
        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get manager statistics.

        Returns:
            Statistics dict
        """
        sources = list(self._sources.values())
        return {
            "total_sources": len(sources),
            "enabled_sources": sum(1 for s in sources if s.is_enabled),
            "by_type": {
                t.value: sum(1 for s in sources if s.config.source_type == t)
                for t in SourceType
            },
            "sources": self.list_sources(),
        }


# Global instance
source_manager = SourceManager()


def get_source_manager() -> SourceManager:
    """Get the global source manager instance.

    Returns:
        SourceManager instance
    """
    return source_manager
