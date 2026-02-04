"""Application settings and configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "scripe"
    env: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///./scripe.db"

    # API Keys
    google_places_api_key: str | None = None
    bing_maps_api_key: str | None = None
    anthropic_api_key: str | None = None  # For AI query interpretation

    # Proxy Configuration
    proxy_urls: list[str] = Field(default_factory=list)  # List of proxy URLs
    proxy_rotation_interval: float = 5.0  # Seconds between proxy switches
    proxy_block_duration: float = 300.0  # 5 minutes block after failure

    # Scraper Settings
    enable_scrapers: bool = True  # Enable web scrapers (SERP, Pagine Gialle)
    scraper_rate_limit: float = 0.5  # Requests per second for scrapers

    # Rate Limiting
    global_max_concurrent_requests: int = 10
    per_domain_max_concurrent: int = 2
    default_rate_limit_per_second: float = 1.0

    # HTTP Client
    request_timeout_seconds: int = 30
    max_retries: int = 3
    user_agent: str = "Scripe/0.1.0 (B2B Lead Research; +https://github.com/yourorg/scripe)"

    # Data Quality
    require_phone: bool = True
    require_website: bool = True
    min_confidence_score: float = 0.5
    min_match_score: float = 0.4

    # Compliance
    respect_robots_txt: bool = True
    enable_source_allowlist: bool = True
    max_pages_per_domain: int = 5

    # Geocoding
    nominatim_email: str = "your-email@example.com"
    nominatim_user_agent: str = "Scripe/0.1.0"


# Global settings instance
settings = Settings()
