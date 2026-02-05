"""Rate limiting configuration for Scripe API."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import settings

# Single shared limiter instance - disabled in non-production environments
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri="memory://",
    enabled=settings.env == "production",
)
