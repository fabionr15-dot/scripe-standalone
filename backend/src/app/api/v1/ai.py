"""AI API v1 endpoints for intelligent search assistance."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.query_interpreter import QueryInterpreter, InterpretedQuery
from app.logging_config import get_logger
from app.quality.tiers import QualityTier, get_tier_requirements, estimate_search_cost

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# ==================== MODELS ====================


class InterpretRequest(BaseModel):
    """Request to interpret a natural language query."""

    query: str = Field(..., min_length=3, max_length=500)
    use_ai: bool = Field(default=True, description="Use AI for complex queries")


class InterpretResponse(BaseModel):
    """Response with interpreted search criteria."""

    # Core search
    categories: list[str]
    keywords: list[str]
    search_query: str  # Combined query string

    # Location
    country: str
    regions: list[str]
    cities: list[str]

    # Filters
    keywords_include: list[str]
    keywords_exclude: list[str]

    # Inferred
    business_type: str | None
    company_size: str | None
    industry: str | None

    # Meta
    confidence: float
    suggestions: list[str]
    original_query: str


class TierInfoResponse(BaseModel):
    """Information about a quality tier."""

    tier: str
    display_name: str
    description: str
    min_score: float
    sources: str
    validations: dict[str, bool]
    cost_per_lead: str
    time_factor: str


class EstimateRequest(BaseModel):
    """Request for search cost estimate."""

    query: str
    country: str = "IT"
    regions: list[str] | None = None
    cities: list[str] | None = None
    target_count: int = Field(default=100, ge=1, le=10000)
    quality_tier: str = "standard"


class EstimateResponse(BaseModel):
    """Search cost and time estimate."""

    target_count: int
    tier: str
    estimated_results: int
    estimated_available: int  # Total available in market
    estimated_time_seconds: int
    estimated_time_display: str
    estimated_cost_credits: float
    cost_per_lead: float
    sources_to_use: int


class SuggestionRequest(BaseModel):
    """Request for autocomplete suggestions."""

    partial: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="category", pattern="^(category|city)$")
    region: str | None = None


# ==================== ENDPOINTS ====================


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_query(request: InterpretRequest):
    """Interpret a natural language search query.

    Converts queries like:
    - "Cerco dentisti a Milano, no corsi di formazione"
    - "Ristoranti vegani in Toscana"
    - "Idraulici nella zona di Roma"

    Into structured search criteria.
    """
    interpreter = QueryInterpreter()

    try:
        result = await interpreter.interpret(request.query, use_ai=request.use_ai)

        return InterpretResponse(
            categories=result.categories,
            keywords=result.keywords,
            search_query=result.to_search_query(),
            country=result.country,
            regions=result.regions,
            cities=result.cities,
            keywords_include=result.keywords_include,
            keywords_exclude=result.keywords_exclude,
            business_type=result.business_type,
            company_size=result.company_size,
            industry=result.industry,
            confidence=result.confidence,
            suggestions=result.suggestions,
            original_query=result.original_query,
        )

    except Exception as e:
        logger.error("interpret_failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Interpretation failed: {str(e)}")


@router.get("/tiers", response_model=list[TierInfoResponse])
async def get_quality_tiers():
    """Get information about all quality tiers.

    Returns details about Basic, Standard, and Premium tiers including:
    - Minimum quality score
    - Number of sources used
    - Validation methods
    - Cost per lead
    """
    tiers = []
    for tier in QualityTier:
        info = get_tier_requirements(tier)
        tiers.append(TierInfoResponse(
            tier=info["tier"],
            display_name=info["display_name"],
            description=info["description"],
            min_score=info["min_score"],
            sources=info["sources"],
            validations=info["validations"],
            cost_per_lead=info["cost_per_lead"],
            time_factor=info["time_factor"],
        ))
    return tiers


@router.get("/tiers/{tier}", response_model=TierInfoResponse)
async def get_tier_info(tier: str):
    """Get information about a specific quality tier."""
    try:
        quality_tier = QualityTier(tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier: {tier}. Valid tiers: basic, standard, premium"
        )

    info = get_tier_requirements(quality_tier)
    return TierInfoResponse(
        tier=info["tier"],
        display_name=info["display_name"],
        description=info["description"],
        min_score=info["min_score"],
        sources=info["sources"],
        validations=info["validations"],
        cost_per_lead=info["cost_per_lead"],
        time_factor=info["time_factor"],
    )


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_search(request: EstimateRequest):
    """Estimate search cost and time.

    Provides estimates for:
    - Expected number of results based on market size
    - Execution time
    - Credit cost
    - Sources that will be used
    """
    try:
        quality_tier = QualityTier(request.quality_tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier: {request.quality_tier}"
        )

    # Extract all countries from regions (format: "country:XX")
    all_countries = [request.country] if request.country else []
    if request.regions:
        for region in request.regions:
            if region.startswith("country:"):
                code = region.replace("country:", "")
                if code not in all_countries:
                    all_countries.append(code)

    # Extract category from query (first word is usually the category)
    category = None
    if request.query:
        # Try to match common categories
        query_lower = request.query.lower()
        category_keywords = [
            "dentist", "dental", "zahnarzt", "zahnärzte", "dentista",
            "doctor", "arzt", "ärzte", "medico",
            "lawyer", "anwalt", "rechtsanwalt", "avvocato",
            "restaurant", "ristorante",
            "hotel", "pharmacy", "apotheke", "farmacia",
            "hairdresser", "friseur", "parrucchiere",
            "accountant", "steuerberater", "commercialista",
            "architect", "architekt", "architetto",
            "plumber", "klempner", "idraulico",
            "electrician", "elektriker", "elettricista",
        ]
        for kw in category_keywords:
            if kw in query_lower:
                # Map to English category for lookup
                if kw in ["zahnarzt", "zahnärzte", "dentista", "dental"]:
                    category = "dentist"
                elif kw in ["arzt", "ärzte", "medico"]:
                    category = "doctor"
                elif kw in ["anwalt", "rechtsanwalt", "avvocato"]:
                    category = "lawyer"
                elif kw in ["ristorante"]:
                    category = "restaurant"
                elif kw in ["apotheke", "farmacia"]:
                    category = "pharmacy"
                elif kw in ["friseur", "parrucchiere"]:
                    category = "hairdresser"
                elif kw in ["steuerberater", "commercialista"]:
                    category = "accountant"
                elif kw in ["architekt", "architetto"]:
                    category = "architect"
                elif kw in ["klempner", "idraulico"]:
                    category = "plumber"
                elif kw in ["elektriker", "elettricista"]:
                    category = "electrician"
                else:
                    category = kw
                break

    # Get first city if provided
    city = request.cities[0] if request.cities else None

    # Get first real region (not country:XX)
    region = None
    if request.regions:
        for r in request.regions:
            if not r.startswith("country:"):
                region = r
                break

    estimate = estimate_search_cost(
        target_count=request.target_count,
        tier=quality_tier,
        country=request.country,
        countries=all_countries if len(all_countries) > 1 else None,
        category=category,
        city=city,
        region=region,
    )

    return EstimateResponse(
        target_count=estimate["target_count"],
        tier=estimate["tier"],
        estimated_results=estimate["estimated_results"],
        estimated_available=estimate["estimated_available"],
        estimated_time_seconds=estimate["estimated_time_seconds"],
        estimated_time_display=estimate["estimated_time_display"],
        estimated_cost_credits=estimate["estimated_cost_credits"],
        cost_per_lead=estimate["cost_per_lead"],
        sources_to_use=estimate["sources_to_use"],
    )


@router.get("/suggestions")
async def get_suggestions(
    partial: str = Query(..., min_length=1, max_length=100),
    type: str = Query(default="category", pattern="^(category|city)$"),
    region: str | None = Query(default=None),
):
    """Get autocomplete suggestions for categories or cities.

    Args:
        partial: Partial text to match
        type: Type of suggestion (category or city)
        region: Optional region filter for city suggestions
    """
    interpreter = QueryInterpreter()

    if type == "category":
        suggestions = interpreter.get_category_suggestions(partial)
    else:
        suggestions = interpreter.get_city_suggestions(partial, region)

    return {
        "suggestions": suggestions,
        "type": type,
        "partial": partial,
    }


@router.get("/categories")
async def list_categories():
    """List all supported business categories.

    Returns Italian category names with their English equivalents.
    """
    from app.ai.query_interpreter import CATEGORY_MAPPINGS

    categories = []
    for it_term, en_terms in CATEGORY_MAPPINGS.items():
        categories.append({
            "italian": it_term,
            "english": en_terms[0] if en_terms else it_term,
            "synonyms": en_terms[1:] if len(en_terms) > 1 else [],
        })

    return {
        "categories": sorted(categories, key=lambda x: x["italian"]),
        "total": len(categories),
    }


@router.get("/regions")
async def list_regions():
    """List all Italian regions with their main cities."""
    from app.ai.query_interpreter import ITALIAN_REGIONS

    regions = []
    for region, cities in ITALIAN_REGIONS.items():
        regions.append({
            "region": region.title(),
            "cities": cities,
            "city_count": len(cities),
        })

    return {
        "regions": sorted(regions, key=lambda x: x["region"]),
        "total": len(regions),
    }
