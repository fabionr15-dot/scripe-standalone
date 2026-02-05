"""Search API v1 endpoints with SSE streaming."""

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.middleware import require_auth
from app.auth.models import UserAccount, UserSearch
from app.logging_config import get_logger
from app.quality.enrichment import EnrichmentPipeline
from app.quality.scorer import QualityScorer
from app.quality.validators import DataValidator
from app.sources.manager import SearchCriteria, SearchProgress, get_source_manager
from app.storage.db import db
from app.storage.models import Company, Run, Search

logger = get_logger(__name__)

router = APIRouter(prefix="/searches", tags=["searches-v1"])


def _verify_search_ownership(session, search_id: int, user_id: int) -> Search:
    """Verify that a search exists and belongs to the user.

    Returns the Search object if authorized, raises 404 otherwise.
    """
    search = session.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Check ownership via UserSearch table
    user_search = session.query(UserSearch).filter(
        UserSearch.search_id == search_id,
        UserSearch.user_id == user_id,
    ).first()

    if not user_search:
        raise HTTPException(status_code=404, detail="Search not found")

    return search


# ==================== MODELS ====================


class QualityTier(str, Enum):
    """Quality tier for search results."""
    BASIC = "basic"          # 40% minimum - 2 sources, format validation
    STANDARD = "standard"    # 60% minimum - 4 sources, MX check, enrichment
    PREMIUM = "premium"      # 80% minimum - all sources, full validation


class SearchCreateV1(BaseModel):
    """Create search request."""
    name: str = Field(..., min_length=1, max_length=200)
    query: str = Field(..., min_length=2, description="Search query (category, keywords)")
    country: str = Field(default="IT", min_length=2, max_length=2)
    regions: list[str] | None = Field(default=None, description="Regions to search in")
    cities: list[str] | None = Field(default=None, description="Cities to search in")
    keywords_include: list[str] | None = Field(default=None, description="Must include these keywords")
    keywords_exclude: list[str] | None = Field(default=None, description="Must not include these keywords")
    target_count: int = Field(default=100, ge=1, le=10000)
    quality_tier: QualityTier = Field(default=QualityTier.STANDARD)
    campaign_id: int | None = Field(default=None, description="Optional campaign to link to")

    # Validation options
    require_phone: bool = True
    require_website: bool = True
    validate_phone: bool = False
    validate_email: bool = False


class SearchEstimate(BaseModel):
    """Estimated search results."""
    estimated_results: int
    estimated_time_seconds: int
    estimated_cost_credits: float
    sources_to_use: list[str]
    quality_tier: QualityTier
    min_quality_score: float


class SearchResponse(BaseModel):
    """Search response."""
    id: int
    name: str
    status: str
    query: str
    country: str
    target_count: int
    quality_tier: str
    created_at: str


class RunProgressEvent(BaseModel):
    """SSE progress event."""
    event: str
    run_id: int
    status: str
    progress_percent: int
    current_source: str | None
    results_found: int
    target_count: int
    message: str | None = None


# ==================== QUALITY TIER CONFIG ====================


QUALITY_TIER_CONFIG = {
    QualityTier.BASIC: {
        "min_score": 0.4,
        "max_sources": 2,
        "validate_phone": False,
        "validate_email": False,
        "enrich_website": False,
        "time_multiplier": 1.0,
        "cost_per_lead": 0.05,
    },
    QualityTier.STANDARD: {
        "min_score": 0.6,
        "max_sources": 4,
        "validate_phone": True,  # Format + carrier check
        "validate_email": True,  # MX check
        "enrich_website": False,
        "time_multiplier": 2.0,
        "cost_per_lead": 0.12,
    },
    QualityTier.PREMIUM: {
        "min_score": 0.8,
        "max_sources": None,  # All sources
        "validate_phone": True,  # Carrier check
        "validate_email": True,  # SMTP check
        "enrich_website": True,  # Website crawling + analysis
        "time_multiplier": 4.0,
        "cost_per_lead": 0.25,
    },
}


# ==================== IN-MEMORY RUN TRACKING ====================

# Track active runs for SSE streaming
_active_runs: dict[int, dict[str, Any]] = {}


# ==================== ENDPOINTS ====================


@router.get("")
async def list_searches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(require_auth),
):
    """List user's searches with pagination."""
    with db.session() as session:
        # Get search IDs owned by this user
        user_search_ids = (
            session.query(UserSearch.search_id)
            .filter(UserSearch.user_id == user.id)
            .subquery()
        )

        query = (
            session.query(Search)
            .filter(Search.id.in_(user_search_ids))
            .order_by(Search.created_at.desc())
        )

        total = query.count()
        searches = query.offset(offset).limit(limit).all()

        items = []
        for s in searches:
            # Get latest run status
            latest_run = (
                session.query(Run)
                .filter(Run.search_id == s.id)
                .order_by(Run.started_at.desc())
                .first()
            )

            company_count = (
                session.query(Company)
                .filter(Company.search_id == s.id)
                .count()
            )

            status = "created"
            if latest_run:
                status = latest_run.status

            items.append({
                "id": str(s.id),
                "name": s.name,
                "query": s.criteria_json.get("query", "") if s.criteria_json else "",
                "status": status,
                "quality_tier": s.criteria_json.get("quality_tier", "standard") if s.criteria_json else "standard",
                "results_count": company_count,
                "created_at": s.created_at.isoformat(),
                "completed_at": latest_run.ended_at.isoformat() if latest_run and latest_run.ended_at else None,
            })

        return {"items": items, "total": total}


@router.post("/estimate", response_model=SearchEstimate)
async def estimate_search(search_data: SearchCreateV1):
    """Estimate search results, time and cost before execution.

    Returns estimated results count, execution time, and credits needed.
    """
    manager = get_source_manager()
    tier_config = QUALITY_TIER_CONFIG[search_data.quality_tier]

    # Get available sources for country
    sources = manager.get_sources_for_country(search_data.country)

    if tier_config["max_sources"]:
        sources = sources[:tier_config["max_sources"]]

    source_names = [s.source_name for s in sources]

    # Estimate results (rough heuristic)
    base_estimate = search_data.target_count
    estimated_results = min(base_estimate, search_data.target_count)

    # Estimate time based on sources and quality tier
    base_time = len(sources) * 10  # 10 seconds per source base
    estimated_time = int(base_time * tier_config["time_multiplier"])

    # Estimate cost
    estimated_cost = estimated_results * tier_config["cost_per_lead"]

    return SearchEstimate(
        estimated_results=estimated_results,
        estimated_time_seconds=estimated_time,
        estimated_cost_credits=round(estimated_cost, 2),
        sources_to_use=source_names,
        quality_tier=search_data.quality_tier,
        min_quality_score=tier_config["min_score"],
    )


@router.post("", response_model=SearchResponse)
async def create_search(search_data: SearchCreateV1, user: UserAccount = Depends(require_auth)):
    """Create a new search.

    Creates the search record but does not start execution.
    Use POST /searches/{id}/run to start the search.
    """
    tier_config = QUALITY_TIER_CONFIG[search_data.quality_tier]

    with db.session() as session:
        # Build criteria JSON
        criteria = {
            "query": search_data.query,
            "country": search_data.country,
            "regions": search_data.regions,
            "cities": search_data.cities,
            "keywords_include": search_data.keywords_include,
            "keywords_exclude": search_data.keywords_exclude,
            "quality_tier": search_data.quality_tier.value,
            "min_quality_score": tier_config["min_score"],
        }

        search = Search(
            campaign_id=search_data.campaign_id,
            name=search_data.name,
            criteria_json=criteria,
            target_count=search_data.target_count,
            require_phone=search_data.require_phone,
            require_website=search_data.require_website,
            validate_phone=search_data.validate_phone or tier_config["validate_phone"],
            validate_email=search_data.validate_email or tier_config["validate_email"],
        )
        session.add(search)
        session.flush()

        # Link search to user
        user_search = UserSearch(
            user_id=user.id,
            search_id=search.id,
            credits_spent=0.0,
        )
        session.add(user_search)
        session.commit()

        logger.info(
            "search_v1_created",
            search_id=search.id,
            user_id=user.id,
            query=search_data.query,
            quality_tier=search_data.quality_tier.value,
        )

        return SearchResponse(
            id=search.id,
            name=search.name,
            status="created",
            query=search_data.query,
            country=search_data.country,
            target_count=search.target_count,
            quality_tier=search_data.quality_tier.value,
            created_at=search.created_at.isoformat(),
        )


@router.get("/{search_id}")
async def get_search(search_id: int, user: UserAccount = Depends(require_auth)):
    """Get search details."""
    with db.session() as session:
        search = _verify_search_ownership(session, search_id, user.id)

        # Get latest run
        latest_run = session.query(Run).filter(
            Run.search_id == search_id
        ).order_by(Run.started_at.desc()).first()

        # Get company count
        company_count = session.query(Company).filter(
            Company.search_id == search_id
        ).count()

        return {
            "id": str(search.id),
            "name": search.name,
            "query": search.criteria_json.get("query", "") if search.criteria_json else "",
            "status": latest_run.status if latest_run else "created",
            "quality_tier": search.criteria_json.get("quality_tier", "standard") if search.criteria_json else "standard",
            "results_count": company_count,
            "criteria": search.criteria_json,
            "target_count": search.target_count,
            "require_phone": search.require_phone,
            "require_website": search.require_website,
            "created_at": search.created_at.isoformat(),
            "completed_at": latest_run.ended_at.isoformat() if latest_run and latest_run.ended_at else None,
            "company_count": company_count,
            "latest_run": {
                "id": latest_run.id,
                "status": latest_run.status,
                "progress_percent": latest_run.progress_percent,
                "found_count": latest_run.found_count,
                "started_at": latest_run.started_at.isoformat(),
                "ended_at": latest_run.ended_at.isoformat() if latest_run.ended_at else None,
            } if latest_run else None,
        }


@router.post("/{search_id}/run")
async def start_search_run(
    search_id: int,
    background_tasks: BackgroundTasks,
    user: UserAccount = Depends(require_auth),
):
    """Start a search run.

    Initiates the search execution in the background.
    Use GET /searches/{search_id}/runs/{run_id}/stream for real-time progress.
    """
    with db.session() as session:
        search = _verify_search_ownership(session, search_id, user.id)

        # Create run record
        run = Run(
            search_id=search_id,
            status="running",
            progress_percent=0,
            current_step="initializing",
            found_count=0,
            discarded_count=0,
            started_at=datetime.utcnow(),
        )
        session.add(run)
        session.commit()
        run_id = run.id

        # Initialize tracking
        _active_runs[run_id] = {
            "status": "running",
            "progress_percent": 0,
            "current_source": None,
            "results_found": 0,
            "target_count": search.target_count,
            "events": [],
        }

        # Start background execution
        background_tasks.add_task(
            _execute_search_run,
            search_id,
            run_id,
            search.criteria_json,
            search.target_count,
        )

        logger.info("search_run_started", search_id=search_id, run_id=run_id)

        return {
            "run_id": run_id,
            "status": "running",
            "stream_url": f"/api/v1/searches/{search_id}/runs/{run_id}/stream",
        }


@router.get("/{search_id}/runs/{run_id}/stream")
async def stream_run_progress(
    search_id: int,
    run_id: int,
    user: UserAccount = Depends(require_auth),
):
    """Stream search run progress via Server-Sent Events (SSE).

    Returns real-time progress updates as the search executes.
    Connect to this endpoint with an EventSource client.
    """
    # Verify ownership and run exists
    with db.session() as session:
        _verify_search_ownership(session, search_id, user.id)

        run = session.query(Run).filter(
            Run.id == run_id,
            Run.search_id == search_id,
        ).first()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        """Generate SSE events."""
        last_event_index = 0

        while True:
            # Check if run is still tracked
            if run_id not in _active_runs:
                # Run completed or not found, send final event
                with db.session() as session:
                    run = session.query(Run).filter(Run.id == run_id).first()
                    if run:
                        event = {
                            "event": "complete",
                            "run_id": run_id,
                            "status": run.status,
                            "progress_percent": 100,
                            "results_found": run.found_count,
                            "target_count": run.found_count,
                            "message": "Search completed",
                        }
                        yield f"data: {json.dumps(event)}\n\n"
                break

            run_data = _active_runs[run_id]

            # Send any new events
            events = run_data.get("events", [])
            while last_event_index < len(events):
                event = events[last_event_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_event_index += 1

            # Send heartbeat/progress
            progress_event = {
                "event": "progress",
                "run_id": run_id,
                "status": run_data["status"],
                "progress_percent": run_data["progress_percent"],
                "current_source": run_data.get("current_source"),
                "results_found": run_data["results_found"],
                "target_count": run_data["target_count"],
            }
            yield f"data: {json.dumps(progress_event)}\n\n"

            await asyncio.sleep(1)  # Update every second

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{search_id}/runs/{run_id}")
async def get_run_status(
    search_id: int,
    run_id: int,
    user: UserAccount = Depends(require_auth),
):
    """Get run status (non-streaming)."""
    with db.session() as session:
        _verify_search_ownership(session, search_id, user.id)

        run = session.query(Run).filter(
            Run.id == run_id,
            Run.search_id == search_id,
        ).first()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Check if still active and merge live data
        is_active = run_id in _active_runs
        live_data = _active_runs.get(run_id, {})

        return {
            "id": run.id,
            "search_id": run.search_id,
            "status": live_data.get("status", run.status) if is_active else run.status,
            "progress_percent": live_data.get("progress_percent", run.progress_percent) if is_active else run.progress_percent,
            "current_source": live_data.get("current_source") if is_active else None,
            "results_found": live_data.get("results_found", run.found_count) if is_active else run.found_count,
            "target_count": live_data.get("target_count", 0) if is_active else run.found_count,
            "current_step": run.current_step,
            "found_count": run.found_count,
            "discarded_count": run.discarded_count,
            "started_at": run.started_at.isoformat(),
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
            "is_active": is_active,
        }


@router.get("/{search_id}/companies")
async def get_search_companies(
    search_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    min_quality: float = Query(default=0.0, ge=0.0, le=1.0),
    has_phone: bool | None = None,
    has_email: bool | None = None,
    has_website: bool | None = None,
    user: UserAccount = Depends(require_auth),
):
    """Get paginated search results with filtering.

    Args:
        search_id: Search ID
        page: Page number (1-indexed)
        page_size: Results per page
        min_quality: Minimum quality score filter
        has_phone: Filter for companies with phone
        has_email: Filter for companies with email
        has_website: Filter for companies with website
    """
    with db.session() as session:
        search = _verify_search_ownership(session, search_id, user.id)

        # Build query
        query = session.query(Company).filter(Company.search_id == search_id)

        # Apply filters
        if min_quality > 0:
            query = query.filter(Company.quality_score >= min_quality)
        if has_phone is True:
            query = query.filter(Company.phone.isnot(None))
        if has_phone is False:
            query = query.filter(Company.phone.is_(None))
        if has_email is True:
            query = query.filter(Company.email.isnot(None))
        if has_email is False:
            query = query.filter(Company.email.is_(None))
        if has_website is True:
            query = query.filter(Company.website.isnot(None))
        if has_website is False:
            query = query.filter(Company.website.is_(None))

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        companies = query.order_by(
            Company.quality_score.desc(),
            Company.match_score.desc(),
        ).offset(offset).limit(page_size).all()

        return {
            "search_id": search_id,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "items": [
                {
                    "id": c.id,
                    "company_name": c.company_name,
                    "website": c.website,
                    "phone": c.phone,
                    "email": c.email,
                    "address_line": c.address_line,
                    "postal_code": c.postal_code,
                    "city": c.city,
                    "region": c.region,
                    "country": c.country,
                    "category": c.category,
                    "quality_score": c.quality_score,
                    "match_score": c.match_score,
                    "confidence_score": c.confidence_score,
                    "phone_validated": c.phone_validated,
                    "email_validated": c.email_validated,
                    "website_validated": c.website_validated,
                }
                for c in companies
            ],
        }


# ==================== BACKGROUND EXECUTION ====================


async def _execute_search_run(
    search_id: int,
    run_id: int,
    criteria: dict,
    target_count: int,
):
    """Execute search run in background.

    Args:
        search_id: Search ID
        run_id: Run ID
        criteria: Search criteria dict
        target_count: Target result count
    """
    manager = get_source_manager()

    def progress_callback(progress: SearchProgress):
        """Update progress tracking."""
        if run_id in _active_runs:
            _active_runs[run_id].update({
                "progress_percent": progress.percent_complete,
                "current_source": progress.current_source,
                "results_found": progress.results_found,
            })

            # Add event
            _active_runs[run_id]["events"].append({
                "event": "source_progress",
                "run_id": run_id,
                "source": progress.current_source,
                "completed_sources": progress.completed_sources,
                "total_sources": progress.total_sources,
                "results_found": progress.results_found,
            })

    try:
        # Build search criteria
        search_criteria = SearchCriteria(
            query=criteria.get("query", ""),
            country=criteria.get("country", "IT"),
            regions=criteria.get("regions"),
            cities=criteria.get("cities"),
            keywords_include=criteria.get("keywords_include"),
            keywords_exclude=criteria.get("keywords_exclude"),
            target_count=target_count,
            max_sources=QUALITY_TIER_CONFIG.get(
                QualityTier(criteria.get("quality_tier", "standard")),
                {}
            ).get("max_sources"),
        )

        # Execute search
        results = await manager.search_cascade(
            search_criteria,
            progress_callback=progress_callback,
        )

        # Get quality tier for this search
        quality_tier = QualityTier(criteria.get("quality_tier", "standard"))
        tier_config = QUALITY_TIER_CONFIG.get(quality_tier, {})

        # --- ENRICHMENT & VALIDATION PIPELINE ---
        if run_id in _active_runs:
            _active_runs[run_id].update({
                "current_source": "validation",
                "progress_percent": 80,
            })

        validator = DataValidator(default_country=criteria.get("country", "IT"))
        scorer = QualityScorer()

        # Determine validation level
        if tier_config.get("enrich_website"):
            validation_level = "premium"
        elif tier_config.get("validate_phone") or tier_config.get("validate_email"):
            validation_level = "standard"
        else:
            validation_level = "basic"

        enriched_results = []
        total_results = len(results)

        for idx, result in enumerate(results):
            try:
                # Build data dict for validation
                lead_data = {
                    "company_name": result.company_name,
                    "phone": result.phone,
                    "email": getattr(result, "email", None),
                    "website": result.website,
                    "address_line": result.address_line,
                    "city": result.city,
                    "region": result.region,
                    "country": result.country,
                    "category": result.category,
                    "source": result.source_name,
                }

                # Run validation based on tier
                validations = await validator.validate_all(lead_data, validation_level)

                # Build validation results dict for scorer
                validation_results = {
                    k: v.is_valid for k, v in validations.items()
                }

                # Calculate quality score
                quality = scorer.score(
                    lead_data,
                    search_criteria=criteria,
                    source_confidence=0.7,
                    validation_results=validation_results,
                )

                enriched_results.append({
                    "result": result,
                    "quality": quality,
                    "validations": validations,
                })

                # Update progress during validation
                if run_id in _active_runs and idx % 5 == 0:
                    validation_progress = 80 + int((idx / max(total_results, 1)) * 20)
                    _active_runs[run_id].update({
                        "progress_percent": min(validation_progress, 99),
                        "current_source": "validation",
                    })

            except Exception as e:
                logger.debug("validation_error", company=result.company_name, error=str(e))
                # Still include with base score on validation error
                enriched_results.append({
                    "result": result,
                    "quality": scorer.score(lead_data, source_confidence=0.5),
                    "validations": {},
                })

        # Save results to database
        with db.session() as session:
            for item in enriched_results:
                result = item["result"]
                quality = item["quality"]
                validations = item.get("validations", {})

                company = Company(
                    search_id=search_id,
                    company_name=result.company_name,
                    website=result.website,
                    phone=result.phone,
                    address_line=result.address_line,
                    postal_code=result.postal_code,
                    city=result.city,
                    region=result.region,
                    country=result.country,
                    category=result.category,
                    source_url=result.source_url,
                    quality_score=int(quality.quality_score * 100),
                    confidence_score=quality.confidence_score,
                    phone_validated=validations.get("phone", None) and validations["phone"].is_valid,
                    email_validated=validations.get("email", None) and validations["email"].is_valid,
                    website_validated=validations.get("website", None) and validations["website"].is_valid,
                )
                session.add(company)

            # Update run status
            run = session.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "completed"
                run.progress_percent = 100
                run.found_count = len(enriched_results)
                run.ended_at = datetime.utcnow()

            session.commit()

        logger.info(
            "search_run_completed",
            search_id=search_id,
            run_id=run_id,
            results_count=len(results),
        )

    except Exception as e:
        logger.error(
            "search_run_failed",
            search_id=search_id,
            run_id=run_id,
            error=str(e),
        )

        # Update run as failed
        with db.session() as session:
            run = session.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.ended_at = datetime.utcnow()
            session.commit()

        if run_id in _active_runs:
            _active_runs[run_id]["status"] = "failed"
            _active_runs[run_id]["events"].append({
                "event": "error",
                "run_id": run_id,
                "message": str(e),
            })

    finally:
        # Cleanup after short delay (allow clients to get final status)
        await asyncio.sleep(5)
        if run_id in _active_runs:
            del _active_runs[run_id]
