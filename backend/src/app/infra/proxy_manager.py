"""Proxy Manager for rotating proxies during scraping."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from app.logging_config import get_logger

logger = get_logger(__name__)


class ProxyStatus(Enum):
    """Proxy status."""
    HEALTHY = "healthy"
    BLOCKED = "blocked"
    SLOW = "slow"
    DEAD = "dead"


@dataclass
class ProxyInfo:
    """Information about a proxy."""
    url: str  # http://user:pass@host:port or http://host:port
    status: ProxyStatus = ProxyStatus.HEALTHY
    last_used: float = 0.0
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    blocked_until: float = 0.0
    average_latency: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def is_available(self) -> bool:
        """Check if proxy is available for use."""
        if self.status == ProxyStatus.DEAD:
            return False
        if self.status == ProxyStatus.BLOCKED:
            return time.time() > self.blocked_until
        return True


@dataclass
class ProxyManagerConfig:
    """Configuration for proxy manager."""
    # Minimum time between uses of same proxy (seconds)
    min_proxy_interval: float = 5.0
    # Time to block a proxy after failure (seconds)
    block_duration: float = 300.0  # 5 minutes
    # Max consecutive failures before marking as dead
    max_consecutive_failures: int = 5
    # Timeout for proxy health checks (seconds)
    health_check_timeout: float = 10.0
    # URLs to use for health checks
    health_check_urls: list[str] = field(default_factory=lambda: [
        "https://httpbin.org/ip",
        "https://api.ipify.org?format=json",
    ])


class ProxyManager:
    """Manages proxy rotation for web scraping.

    Features:
    - Round-robin rotation with health tracking
    - Automatic blocking of failing proxies
    - Latency-based selection
    - Health check capabilities
    - Support for multiple proxy providers
    """

    def __init__(self, config: ProxyManagerConfig | None = None):
        """Initialize proxy manager.

        Args:
            config: Optional configuration
        """
        self.config = config or ProxyManagerConfig()
        self._proxies: dict[str, ProxyInfo] = {}
        self._proxy_order: list[str] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)

    def add_proxy(self, proxy_url: str) -> None:
        """Add a proxy to the pool.

        Args:
            proxy_url: Proxy URL (http://user:pass@host:port)
        """
        if proxy_url not in self._proxies:
            self._proxies[proxy_url] = ProxyInfo(url=proxy_url)
            self._proxy_order.append(proxy_url)
            self.logger.info("proxy_added", proxy=self._mask_proxy(proxy_url))

    def add_proxies(self, proxy_urls: list[str]) -> None:
        """Add multiple proxies to the pool.

        Args:
            proxy_urls: List of proxy URLs
        """
        for url in proxy_urls:
            self.add_proxy(url)

    def remove_proxy(self, proxy_url: str) -> None:
        """Remove a proxy from the pool.

        Args:
            proxy_url: Proxy URL to remove
        """
        if proxy_url in self._proxies:
            del self._proxies[proxy_url]
            self._proxy_order.remove(proxy_url)
            self.logger.info("proxy_removed", proxy=self._mask_proxy(proxy_url))

    async def get_proxy(self) -> str | None:
        """Get the next available proxy.

        Uses round-robin selection with health-based filtering.

        Returns:
            Proxy URL or None if no proxies available
        """
        async with self._lock:
            if not self._proxies:
                return None

            now = time.time()
            available = []

            # Find available proxies
            for url, info in self._proxies.items():
                if not info.is_available:
                    continue

                # Check if enough time has passed since last use
                time_since_use = now - info.last_used
                if time_since_use < self.config.min_proxy_interval:
                    continue

                available.append((url, info))

            if not available:
                # All proxies are in cooldown - return the one with shortest wait
                best = min(
                    [(url, info) for url, info in self._proxies.items() if info.is_available],
                    key=lambda x: x[1].last_used,
                    default=(None, None)
                )
                if best[0]:
                    proxy_url = best[0]
                    self._proxies[proxy_url].last_used = now
                    self._proxies[proxy_url].use_count += 1
                    return proxy_url
                return None

            # Select based on success rate and latency
            # Prefer proxies with higher success rate and lower latency
            def score(item: tuple[str, ProxyInfo]) -> float:
                url, info = item
                success_factor = info.success_rate
                latency_factor = 1 / (1 + info.average_latency)  # Lower latency = higher score
                return success_factor * latency_factor

            # Sort by score (highest first) and pick from top proxies with some randomness
            sorted_proxies = sorted(available, key=score, reverse=True)

            # Pick randomly from top 3 to add some variation
            top_proxies = sorted_proxies[:min(3, len(sorted_proxies))]
            proxy_url, _ = random.choice(top_proxies)

            # Update proxy info
            self._proxies[proxy_url].last_used = now
            self._proxies[proxy_url].use_count += 1

            return proxy_url

    async def report_success(self, proxy_url: str, latency: float | None = None) -> None:
        """Report successful use of a proxy.

        Args:
            proxy_url: Proxy URL that succeeded
            latency: Request latency in seconds
        """
        async with self._lock:
            if proxy_url in self._proxies:
                info = self._proxies[proxy_url]
                info.success_count += 1
                info.status = ProxyStatus.HEALTHY

                if latency is not None:
                    # Update moving average latency
                    if info.average_latency == 0:
                        info.average_latency = latency
                    else:
                        info.average_latency = info.average_latency * 0.7 + latency * 0.3

                self.logger.debug(
                    "proxy_success",
                    proxy=self._mask_proxy(proxy_url),
                    latency=latency,
                    success_rate=info.success_rate,
                )

    async def report_blocked(self, proxy_url: str) -> None:
        """Report that a proxy was blocked.

        Args:
            proxy_url: Proxy URL that was blocked
        """
        async with self._lock:
            if proxy_url in self._proxies:
                info = self._proxies[proxy_url]
                info.failure_count += 1
                info.status = ProxyStatus.BLOCKED
                info.blocked_until = time.time() + self.config.block_duration

                # Check if proxy should be marked as dead
                consecutive_failures = info.failure_count - info.success_count
                if consecutive_failures >= self.config.max_consecutive_failures:
                    info.status = ProxyStatus.DEAD
                    self.logger.warning(
                        "proxy_marked_dead",
                        proxy=self._mask_proxy(proxy_url),
                        failures=info.failure_count,
                    )
                else:
                    self.logger.info(
                        "proxy_blocked",
                        proxy=self._mask_proxy(proxy_url),
                        blocked_until=info.blocked_until,
                    )

    async def report_failure(self, proxy_url: str) -> None:
        """Report a general failure (timeout, connection error).

        Args:
            proxy_url: Proxy URL that failed
        """
        await self.report_blocked(proxy_url)

    async def health_check(self, proxy_url: str) -> bool:
        """Check if a proxy is healthy.

        Args:
            proxy_url: Proxy URL to check

        Returns:
            True if healthy
        """
        try:
            start = time.time()
            async with httpx.AsyncClient(
                proxies={"all://": proxy_url},
                timeout=self.config.health_check_timeout,
            ) as client:
                # Try each health check URL
                for url in self.config.health_check_urls:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            latency = time.time() - start
                            await self.report_success(proxy_url, latency)
                            return True
                    except Exception:
                        continue

                # All URLs failed
                await self.report_failure(proxy_url)
                return False

        except Exception as e:
            self.logger.debug("proxy_health_check_failed", proxy=self._mask_proxy(proxy_url), error=str(e))
            await self.report_failure(proxy_url)
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all proxies.

        Returns:
            Dict of proxy URL -> is_healthy
        """
        tasks = [
            self.health_check(url)
            for url in self._proxies.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            url: result if isinstance(result, bool) else False
            for url, result in zip(self._proxies.keys(), results)
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the proxy pool.

        Returns:
            Statistics dict
        """
        total = len(self._proxies)
        healthy = sum(1 for p in self._proxies.values() if p.status == ProxyStatus.HEALTHY)
        blocked = sum(1 for p in self._proxies.values() if p.status == ProxyStatus.BLOCKED)
        dead = sum(1 for p in self._proxies.values() if p.status == ProxyStatus.DEAD)

        return {
            "total_proxies": total,
            "healthy": healthy,
            "blocked": blocked,
            "dead": dead,
            "available": sum(1 for p in self._proxies.values() if p.is_available),
            "average_success_rate": sum(p.success_rate for p in self._proxies.values()) / max(total, 1),
            "proxies": [
                {
                    "url": self._mask_proxy(url),
                    "status": info.status.value,
                    "success_rate": info.success_rate,
                    "use_count": info.use_count,
                    "average_latency": info.average_latency,
                }
                for url, info in self._proxies.items()
            ],
        }

    def _mask_proxy(self, proxy_url: str) -> str:
        """Mask proxy URL for logging (hide credentials).

        Args:
            proxy_url: Full proxy URL

        Returns:
            Masked URL
        """
        # Hide username:password if present
        if "@" in proxy_url:
            # http://user:pass@host:port -> http://****@host:port
            parts = proxy_url.split("@")
            return f"****@{parts[-1]}"
        return proxy_url

    async def rotate(self) -> str | None:
        """Force rotation to next proxy.

        Returns:
            Next proxy URL
        """
        return await self.get_proxy()


# Global instance
_proxy_manager: ProxyManager | None = None


def get_proxy_manager() -> ProxyManager:
    """Get the global proxy manager instance.

    Returns:
        ProxyManager instance
    """
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def configure_proxy_manager(proxies: list[str], config: ProxyManagerConfig | None = None) -> ProxyManager:
    """Configure the global proxy manager.

    Args:
        proxies: List of proxy URLs
        config: Optional configuration

    Returns:
        Configured ProxyManager instance
    """
    global _proxy_manager
    _proxy_manager = ProxyManager(config)
    _proxy_manager.add_proxies(proxies)
    return _proxy_manager
