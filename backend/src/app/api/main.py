"""Main FastAPI application for Scripe API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.rate_limit import limiter
from app.api.routes import get_routers
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.export import router as export_router
from app.api.v1.searches import router as searches_v1_router
from app.api.v1.sources import router as sources_router
from app.api.v1.webhooks import router as webhooks_router
from app.logging_config import get_logger
from app.settings import settings
from app.sources.setup import setup_sources
from app.storage.db import db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("app_starting", env=settings.env)

    # Initialize database tables
    db.create_tables()
    logger.info("database_tables_created")

    # Setup data sources
    setup_sources(
        enable_scrapers=settings.enable_scrapers,
        proxy_list=settings.proxy_urls if settings.proxy_urls else None,
    )
    logger.info("sources_initialized")

    yield

    # Shutdown
    logger.info("app_shutting_down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    # Hide API docs in production
    is_production = settings.env == "production"

    app = FastAPI(
        title="Scripe API",
        description="B2B Lead Generation Platform API",
        version="1.0.0",
        docs_url=None if is_production else "/api/docs",
        redoc_url=None if is_production else "/api/redoc",
        openapi_url=None if is_production else "/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware - restrict origins in production
    allowed_origins = (
        settings.allowed_origins.split(",")
        if is_production
        else ["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting (shared instance from rate_limit module)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Troppe richieste. Riprova tra poco."},
        )

    # Include legacy routers (v0)
    for router in get_routers():
        app.include_router(router, prefix="/api")

    # Include v1 API routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(searches_v1_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "env": settings.env,
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Scripe API",
            "version": "1.0.0",
            "docs": "/api/docs",
        }

    return app


# Create app instance
app = create_app()
