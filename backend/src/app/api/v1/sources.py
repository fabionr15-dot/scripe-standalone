"""Sources API v1 endpoints."""

from fastapi import APIRouter, HTTPException

from app.logging_config import get_logger
from app.sources.manager import get_source_manager
from app.infra.proxy_manager import get_proxy_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def list_sources():
    """List all registered data sources.

    Returns sources with their configuration and status.
    """
    manager = get_source_manager()
    sources = manager.list_sources()

    return {
        "sources": sources,
        "total": len(sources),
        "enabled": sum(1 for s in sources if s["enabled"]),
    }


@router.get("/{source_name}")
async def get_source(source_name: str):
    """Get detailed information about a specific source."""
    manager = get_source_manager()
    source = manager.get_source(source_name)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return {
        "name": source.source_name,
        "type": source.config.source_type.value,
        "priority": source.config.priority,
        "enabled": source.is_enabled,
        "countries": source.config.supported_countries,
        "requires_api_key": source.config.requires_api_key,
        "confidence_score": source.config.confidence_score,
        "rate_limit": source.config.rate_limit,
        "requires_proxy": source.config.requires_proxy,
        "is_healthy": source._is_healthy,
        "last_error": source._last_error,
    }


@router.post("/{source_name}/health-check")
async def check_source_health(source_name: str):
    """Check health of a specific source.

    Performs an active health check and returns the result.
    """
    manager = get_source_manager()
    source = manager.get_source(source_name)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        is_healthy = await source.health_check()
        return {
            "source": source_name,
            "is_healthy": is_healthy,
            "last_error": source._last_error,
        }
    except Exception as e:
        logger.error("source_health_check_failed", source=source_name, error=str(e))
        return {
            "source": source_name,
            "is_healthy": False,
            "error": str(e),
        }


@router.get("/health/all")
async def check_all_sources_health():
    """Check health of all registered sources."""
    manager = get_source_manager()
    results = await manager.health_check_all()

    return {
        "results": results,
        "healthy_count": sum(1 for v in results.values() if v),
        "total_count": len(results),
    }


@router.get("/for-country/{country}")
async def get_sources_for_country(country: str):
    """Get sources that support a specific country.

    Args:
        country: Country code (e.g., 'IT', 'DE', 'US')
    """
    manager = get_source_manager()
    sources = manager.get_sources_for_country(country.upper())

    return {
        "country": country.upper(),
        "sources": [
            {
                "name": s.source_name,
                "type": s.config.source_type.value,
                "priority": s.config.priority,
                "enabled": s.is_enabled,
            }
            for s in sources
        ],
        "count": len(sources),
    }


@router.get("/statistics")
async def get_sources_statistics():
    """Get overall statistics about data sources."""
    manager = get_source_manager()
    stats = manager.get_statistics()

    return stats


# ==================== PROXY ENDPOINTS ====================


@router.get("/proxies/statistics")
async def get_proxy_statistics():
    """Get statistics about the proxy pool."""
    proxy_manager = get_proxy_manager()
    return proxy_manager.get_statistics()


@router.post("/proxies/health-check")
async def check_all_proxies_health():
    """Check health of all proxies in the pool."""
    proxy_manager = get_proxy_manager()
    results = await proxy_manager.health_check_all()

    return {
        "results": {
            proxy_manager._mask_proxy(url): healthy
            for url, healthy in results.items()
        },
        "healthy_count": sum(1 for v in results.values() if v),
        "total_count": len(results),
    }
