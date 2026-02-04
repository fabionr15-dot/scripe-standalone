"""HTTP client with rate limiting and robots.txt compliance."""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from scripe.logging_config import get_logger
from scripe.settings import settings

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter for HTTP requests."""

    def __init__(self, global_limit: int, per_domain_limit: int, delay_ms: int):
        self.global_semaphore = asyncio.Semaphore(global_limit)
        self.domain_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_domain_limit)
        )
        self.last_request: dict[str, datetime] = {}
        self.delay = timedelta(milliseconds=delay_ms)

    async def acquire(self, domain: str) -> None:
        """Acquire rate limit for domain."""
        async with self.global_semaphore:
            async with self.domain_semaphores[domain]:
                # Enforce minimum delay between requests
                if domain in self.last_request:
                    elapsed = datetime.now() - self.last_request[domain]
                    if elapsed < self.delay:
                        wait_time = (self.delay - elapsed).total_seconds()
                        await asyncio.sleep(wait_time)

                self.last_request[domain] = datetime.now()


class RobotsChecker:
    """Robots.txt compliance checker."""

    def __init__(self):
        self.parsers: dict[str, RobotFileParser] = {}
        self.failed_domains: set[str] = set()

    async def can_fetch(self, url: str, user_agent: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not settings.respect_robots_txt:
            return True

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain in self.failed_domains:
            return True  # If robots.txt failed to load, allow crawling

        if domain not in self.parsers:
            await self._load_robots(domain, user_agent)

        if domain in self.failed_domains:
            return True

        parser = self.parsers[domain]
        return parser.can_fetch(user_agent, url)

    async def _load_robots(self, domain: str, user_agent: str) -> None:
        """Load robots.txt for domain."""
        robots_url = f"{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    robots_url,
                    headers={"User-Agent": user_agent},
                    follow_redirects=True,
                )
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                    self.parsers[domain] = parser
                    logger.info("robots_txt_loaded", domain=domain)
                else:
                    self.failed_domains.add(domain)
                    logger.warning("robots_txt_not_found", domain=domain, status=response.status_code)
        except Exception as e:
            self.failed_domains.add(domain)
            logger.warning("robots_txt_load_error", domain=domain, error=str(e))


class HTTPClient:
    """HTTP client with rate limiting and compliance."""

    def __init__(self):
        self.rate_limiter = RateLimiter(
            global_limit=settings.global_rate_limit,
            per_domain_limit=settings.per_domain_rate_limit,
            delay_ms=settings.request_delay_ms,
        )
        self.robots_checker = RobotsChecker()
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched."""
        return await self.robots_checker.can_fetch(url, settings.user_agent)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET request with rate limiting and retry."""
        parsed = urlparse(url)
        domain = parsed.netloc

        # Check robots.txt
        if not await self.can_fetch(url):
            logger.warning("url_blocked_by_robots", url=url)
            raise ValueError(f"URL blocked by robots.txt: {url}")

        # Rate limiting
        await self.rate_limiter.acquire(domain)

        # Make request
        logger.debug("http_get", url=url, domain=domain)
        response = await self.client.get(url, **kwargs)
        response.raise_for_status()

        return response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
