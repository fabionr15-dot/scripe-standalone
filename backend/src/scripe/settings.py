"""Application settings and configuration."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SCRIPE_",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./scripe.db",
        description="Database connection URL",
    )

    # HTTP Client
    user_agent: str = Field(
        default="Scripe/0.1.0 (B2B Lead Research Tool; +https://github.com/yourorg/scripe)",
        description="User-Agent header for HTTP requests",
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests",
    )

    # Rate Limiting
    global_rate_limit: int = Field(
        default=10,
        description="Maximum concurrent requests globally",
    )
    per_domain_rate_limit: int = Field(
        default=2,
        description="Maximum concurrent requests per domain",
    )
    request_delay_ms: int = Field(
        default=1000,
        description="Minimum delay between requests to same domain (ms)",
    )

    # Google Places API (optional)
    google_places_api_key: str | None = Field(
        default=None,
        description="Google Places API key for enrichment",
    )

    # Paths
    data_dir: Path = Field(
        default=Path("./data"),
        description="Directory for data files",
    )
    exports_dir: Path = Field(
        default=Path("./exports"),
        description="Directory for exported files",
    )
    logs_dir: Path = Field(
        default=Path("./logs"),
        description="Directory for log files",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["console", "json"] = Field(
        default="console",
        description="Log output format",
    )

    # Compliance
    respect_robots_txt: bool = Field(
        default=True,
        description="Respect robots.txt files",
    )
    max_pages_per_domain: int = Field(
        default=5,
        description="Maximum pages to crawl per domain",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
