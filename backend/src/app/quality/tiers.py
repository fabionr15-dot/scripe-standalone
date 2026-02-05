"""Quality tier definitions and configuration."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QualityTier(str, Enum):
    """Quality tier levels for lead data."""

    BASIC = "basic"        # 40-59% - Basic data, format validated
    STANDARD = "standard"  # 60-79% - Good data, MX/domain validated
    PREMIUM = "premium"    # 80-100% - Excellent data, fully validated

    @classmethod
    def from_score(cls, score: float) -> "QualityTier":
        """Get tier from quality score.

        Args:
            score: Quality score (0-1)

        Returns:
            Appropriate quality tier
        """
        if score >= 0.8:
            return cls.PREMIUM
        elif score >= 0.6:
            return cls.STANDARD
        else:
            return cls.BASIC


@dataclass
class TierConfig:
    """Configuration for a quality tier."""

    tier: QualityTier
    min_score: float
    max_score: float

    # Source requirements
    min_sources: int
    max_sources: int | None  # None = all available

    # Validation requirements
    validate_phone_format: bool
    validate_phone_carrier: bool  # Expensive - carrier lookup
    validate_email_format: bool
    validate_email_mx: bool
    validate_email_smtp: bool  # Expensive - SMTP check
    validate_website: bool
    enrich_from_website: bool

    # Time/Cost factors
    time_multiplier: float
    cost_per_lead: float

    # Display
    display_name: str
    description: str


# Tier configurations
TIER_CONFIG: dict[QualityTier, TierConfig] = {
    QualityTier.BASIC: TierConfig(
        tier=QualityTier.BASIC,
        min_score=0.4,
        max_score=0.59,
        min_sources=1,
        max_sources=2,
        validate_phone_format=True,
        validate_phone_carrier=False,
        validate_email_format=True,
        validate_email_mx=False,
        validate_email_smtp=False,
        validate_website=False,
        enrich_from_website=False,
        time_multiplier=1.0,
        cost_per_lead=0.05,
        display_name="Basic",
        description="Dati base con validazione formato. Ideale per campagne di volume.",
    ),
    QualityTier.STANDARD: TierConfig(
        tier=QualityTier.STANDARD,
        min_score=0.6,
        max_score=0.79,
        min_sources=2,
        max_sources=4,
        validate_phone_format=True,
        validate_phone_carrier=False,
        validate_email_format=True,
        validate_email_mx=True,
        validate_email_smtp=False,
        validate_website=True,
        enrich_from_website=True,
        time_multiplier=2.0,
        cost_per_lead=0.12,
        display_name="Standard",
        description="Dati verificati con controllo telefono e sito web. Qualità garantita.",
    ),
    QualityTier.PREMIUM: TierConfig(
        tier=QualityTier.PREMIUM,
        min_score=0.8,
        max_score=1.0,
        min_sources=3,
        max_sources=None,
        validate_phone_format=True,
        validate_phone_carrier=True,
        validate_email_format=True,
        validate_email_mx=True,
        validate_email_smtp=True,
        validate_website=True,
        enrich_from_website=True,
        time_multiplier=4.0,
        cost_per_lead=0.25,
        display_name="Premium",
        description="Dati completamente verificati con analisi sito web. Massima qualità.",
    ),
}


def get_tier_for_score(score: float) -> TierConfig:
    """Get tier configuration for a quality score.

    Args:
        score: Quality score (0-1)

    Returns:
        Tier configuration
    """
    tier = QualityTier.from_score(score)
    return TIER_CONFIG[tier]


def get_tier_requirements(tier: QualityTier) -> dict[str, Any]:
    """Get human-readable requirements for a tier.

    Args:
        tier: Quality tier

    Returns:
        Requirements dictionary
    """
    config = TIER_CONFIG[tier]
    return {
        "tier": tier.value,
        "display_name": config.display_name,
        "description": config.description,
        "min_score": config.min_score,
        "sources": f"{config.min_sources}-{config.max_sources or 'all'}",
        "validations": {
            "phone_format": config.validate_phone_format,
            "phone_carrier": config.validate_phone_carrier,
            "email_format": config.validate_email_format,
            "email_mx": config.validate_email_mx,
            "email_smtp": config.validate_email_smtp,
            "website": config.validate_website,
            "enrichment": config.enrich_from_website,
        },
        "cost_per_lead": f"€{config.cost_per_lead:.2f}",
        "time_factor": f"{config.time_multiplier}x",
    }


def estimate_search_cost(
    target_count: int,
    tier: QualityTier,
    country: str | None = None,
    countries: list[str] | None = None,
    category: str | None = None,
    city: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Estimate search cost and available leads for given criteria.

    Args:
        target_count: Target number of leads
        tier: Quality tier
        country: Primary country code (DE, AT, CH, IT, etc.)
        countries: List of all country codes for multi-country search
        category: Business category (dentist, restaurant, etc.)
        city: Specific city (limits results)
        region: Specific region (limits results)

    Returns:
        Cost estimate with realistic lead counts
    """
    config = TIER_CONFIG[tier]

    # Calculate estimated available leads based on market data
    estimated_available = _estimate_market_size(
        country=country,
        countries=countries,
        category=category,
        city=city,
        region=region,
    )

    # How many leads we'll actually collect (capped by what's available)
    leads_to_collect = min(target_count, estimated_available)

    # Base time per 100 leads
    base_time_per_100 = 60  # 1 minute per 100 leads base

    # Calculate time based on leads to collect (not total market)
    sources_to_use = config.max_sources or 5
    estimated_time = (leads_to_collect / 100) * base_time_per_100 * config.time_multiplier

    # Minimum time of 30 seconds
    estimated_time = max(30, estimated_time)

    # Calculate cost based on leads to collect
    estimated_cost = leads_to_collect * config.cost_per_lead

    return {
        "target_count": target_count,
        "tier": tier.value,
        "estimated_results": leads_to_collect,
        "estimated_available": estimated_available,
        "estimated_time_seconds": int(estimated_time),
        "estimated_time_display": _format_duration(int(estimated_time)),
        "estimated_cost_credits": round(estimated_cost, 2),
        "cost_per_lead": config.cost_per_lead,
        "sources_to_use": sources_to_use,
    }


# Market size estimates by country and category (approximate business counts)
MARKET_SIZE_ESTIMATES: dict[str, dict[str, int]] = {
    # Germany - ~3.7M businesses
    "DE": {
        "dentist": 65000,
        "dental clinic": 65000,
        "doctor": 150000,
        "medical practice": 150000,
        "pharmacy": 19000,
        "restaurant": 220000,
        "hotel": 50000,
        "lawyer": 165000,
        "law firm": 165000,
        "accountant": 95000,
        "architect": 45000,
        "hairdresser": 80000,
        "gym": 10000,
        "fitness center": 10000,
        "plumber": 50000,
        "electrician": 55000,
        "default": 50000,
    },
    # Austria - ~600K businesses
    "AT": {
        "dentist": 5500,
        "dental clinic": 5500,
        "doctor": 18000,
        "medical practice": 18000,
        "pharmacy": 1400,
        "restaurant": 35000,
        "hotel": 15000,
        "lawyer": 6500,
        "law firm": 6500,
        "accountant": 8500,
        "architect": 4000,
        "hairdresser": 8000,
        "gym": 1500,
        "plumber": 5000,
        "electrician": 6000,
        "default": 5000,
    },
    # Switzerland - ~600K businesses
    "CH": {
        "dentist": 4500,
        "dental clinic": 4500,
        "doctor": 20000,
        "medical practice": 20000,
        "pharmacy": 1800,
        "restaurant": 25000,
        "hotel": 5500,
        "lawyer": 11000,
        "law firm": 11000,
        "accountant": 7000,
        "architect": 3500,
        "hairdresser": 6000,
        "gym": 1200,
        "plumber": 4000,
        "electrician": 5000,
        "default": 4000,
    },
    # Italy - ~4.4M businesses
    "IT": {
        "dentist": 60000,
        "dental clinic": 60000,
        "doctor": 240000,
        "medical practice": 240000,
        "pharmacy": 19000,
        "restaurant": 330000,
        "hotel": 33000,
        "lawyer": 250000,
        "law firm": 250000,
        "accountant": 120000,
        "architect": 155000,
        "hairdresser": 95000,
        "gym": 7000,
        "plumber": 35000,
        "electrician": 45000,
        "default": 50000,
    },
    # France - ~4.5M businesses
    "FR": {
        "dentist": 43000,
        "dental clinic": 43000,
        "doctor": 230000,
        "medical practice": 230000,
        "pharmacy": 21000,
        "restaurant": 175000,
        "hotel": 30000,
        "lawyer": 70000,
        "law firm": 70000,
        "accountant": 21000,
        "architect": 30000,
        "hairdresser": 85000,
        "gym": 4500,
        "plumber": 40000,
        "electrician": 50000,
        "default": 40000,
    },
    # Default for unknown countries
    "default": {
        "dentist": 10000,
        "dental clinic": 10000,
        "doctor": 50000,
        "restaurant": 50000,
        "hotel": 10000,
        "lawyer": 20000,
        "default": 10000,
    },
}


def _estimate_market_size(
    country: str | None = None,
    countries: list[str] | None = None,
    category: str | None = None,
    city: str | None = None,
    region: str | None = None,
) -> int:
    """Estimate total available businesses based on criteria.

    Args:
        country: Primary country code
        countries: All country codes (for multi-country)
        category: Business category
        city: Specific city
        region: Specific region

    Returns:
        Estimated number of available businesses
    """
    # Collect all countries
    all_countries = []
    if countries:
        all_countries.extend(countries)
    if country and country not in all_countries:
        all_countries.append(country)
    if not all_countries:
        all_countries = ["IT"]  # Default

    # Calculate total market size across all countries
    total_size = 0
    for c in all_countries:
        country_data = MARKET_SIZE_ESTIMATES.get(c, MARKET_SIZE_ESTIMATES["default"])

        # Get category-specific count or default
        if category:
            cat_lower = category.lower()
            cat_count = country_data.get(cat_lower, country_data.get("default", 10000))
        else:
            cat_count = country_data.get("default", 10000)

        total_size += cat_count

    # Apply geographic filters
    if city:
        # City typically has 1-5% of country's businesses depending on size
        # Major cities (Berlin, Wien, Zürich) have more
        major_cities = ["berlin", "hamburg", "münchen", "köln", "frankfurt",
                        "wien", "zürich", "genf", "basel", "milano", "roma",
                        "paris", "lyon", "marseille"]
        if city.lower() in major_cities:
            total_size = int(total_size * 0.08)  # 8% for major cities
        else:
            total_size = int(total_size * 0.02)  # 2% for smaller cities

    elif region:
        # Region typically has 5-15% of country's businesses
        total_size = int(total_size * 0.10)

    # Ensure minimum of 100 for any search
    return max(100, total_size)


def _format_duration(seconds: int) -> str:
    """Format duration in human readable form."""
    if seconds < 60:
        return f"{seconds} secondi"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minuti"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ore {minutes} minuti"
