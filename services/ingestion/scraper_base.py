"""State-of-art scraper foundation for terra-os ingestion services.

Provides:
  - AsyncHTTPClient  : httpx.AsyncClient with retry, backoff, circuit breaker,
                       connection pool, User-Agent rotation, timeout tiers
  - ScraperMetrics   : per-scraper Prometheus-style counters (in-memory, exported via /metrics)
  - RateLimiter      : async token-bucket per domain
  - RetryPolicy      : exponential backoff with jitter (configurable)
  - ScraperBase      : ABC — async context manager, inherits all of above

Usage:
    class BZPConnector(ScraperBase):
        SOURCE = "bzp"
        async def fetch_page(self, page: int) -> list[dict]:
            resp = await self.get(URL, params={...})
            return resp.json()

    async with BZPConnector() as c:
        data = await c.fetch_page(1)
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, ClassVar, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    "Mozilla/5.0 (compatible; TerraOS/2.0; +https://terra.os)",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
]

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
DOWNLOAD_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
FAST_TIMEOUT = httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=3.0)

DEFAULT_LIMITS = httpx.Limits(
    max_connections=20,
    max_keepalive_connections=10,
    keepalive_expiry=30,
)


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.PoolTimeout,
)


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.3          # ± fraction of computed delay
    backoff_factor: float = 2.0

    def delay_for(self, attempt: int) -> float:
        """Exponential backoff with full-jitter."""
        raw = self.base_delay * (self.backoff_factor ** (attempt - 1))
        capped = min(raw, self.max_delay)
        jitter_range = capped * self.jitter
        return capped + random.uniform(-jitter_range, jitter_range)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"       # normal, requests go through
    OPEN = "open"           # failing, requests blocked
    HALF_OPEN = "half_open" # probe — one request allowed


@dataclass
class CircuitBreaker:
    """Per-domain simple circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds before HALF_OPEN probe

    _failures: int = field(default=0, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _opened_at: float = field(default=0.0, repr=False)

    def record_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.warning("CircuitBreaker OPEN after %d failures", self._failures)

    def allow_request(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("CircuitBreaker → HALF_OPEN (probe)")
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    @property
    def state(self) -> CircuitState:
        return self._state


# ---------------------------------------------------------------------------
# Rate Limiter (async token bucket)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Async token-bucket rate limiter per domain (default: 2 req/s)."""

    def __init__(self, rate: float = 2.0, burst: int = 5):
        self._rate = rate
        self._burst = burst
        self._tokens: dict[str, float] = defaultdict(lambda: float(burst))
        self._last_refill: dict[str, float] = defaultdict(time.monotonic)
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill[domain]
            self._tokens[domain] = min(
                self._burst,
                self._tokens[domain] + elapsed * self._rate
            )
            self._last_refill[domain] = now

            if self._tokens[domain] >= 1.0:
                self._tokens[domain] -= 1.0
                return

            wait = (1.0 - self._tokens[domain]) / self._rate

        await asyncio.sleep(wait)
        await self.acquire(domain)   # recurse after sleep (lock released)


# ---------------------------------------------------------------------------
# Scraper Metrics (in-memory, thread-safe via asyncio)
# ---------------------------------------------------------------------------

class ScraperMetrics:
    """Lightweight in-memory metrics registry — zero external deps."""

    _registry: ClassVar[dict[str, "ScraperMetrics"]] = {}

    def __init__(self, source: str):
        self.source = source
        self.requests_total: int = 0
        self.requests_ok: int = 0
        self.requests_error: int = 0
        self.requests_retried: int = 0
        self.circuit_open_blocks: int = 0
        self.items_fetched: int = 0
        self.items_saved: int = 0
        self.bytes_downloaded: int = 0
        self._latencies: deque[float] = deque(maxlen=200)
        ScraperMetrics._registry[source] = self

    def record_request(self, ok: bool, latency_ms: float, retried: bool = False) -> None:
        self.requests_total += 1
        if ok:
            self.requests_ok += 1
        else:
            self.requests_error += 1
        if retried:
            self.requests_retried += 1
        self._latencies.append(latency_ms)

    def record_items(self, fetched: int = 0, saved: int = 0, bytes_dl: int = 0) -> None:
        self.items_fetched += fetched
        self.items_saved += saved
        self.bytes_downloaded += bytes_dl

    def record_circuit_block(self) -> None:
        self.circuit_open_blocks += 1

    @property
    def p50_ms(self) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        return s[len(s) // 2]

    @property
    def p99_ms(self) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        return s[int(len(s) * 0.99)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "requests": {
                "total": self.requests_total,
                "ok": self.requests_ok,
                "error": self.requests_error,
                "retried": self.requests_retried,
                "circuit_blocks": self.circuit_open_blocks,
            },
            "items": {
                "fetched": self.items_fetched,
                "saved": self.items_saved,
                "bytes_downloaded": self.bytes_downloaded,
            },
            "latency_ms": {
                "p50": round(self.p50_ms, 1),
                "p99": round(self.p99_ms, 1),
            },
        }

    @classmethod
    def all(cls) -> list[dict]:
        return [m.to_dict() for m in cls._registry.values()]


# ---------------------------------------------------------------------------
# Async HTTP Client (core engine)
# ---------------------------------------------------------------------------

class AsyncHTTPClient:
    """Production-grade async HTTP client.

    Features:
    - httpx.AsyncClient with connection pool
    - Per-domain circuit breaker
    - Async token-bucket rate limiter
    - Exponential backoff retry
    - Latency / success metrics
    - User-Agent rotation
    - Structured error logging
    """

    def __init__(
        self,
        source: str,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        limits: httpx.Limits = DEFAULT_LIMITS,
        retry: RetryPolicy | None = None,
        rate_per_second: float = 2.0,
        burst: int = 5,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ):
        self._source = source
        self._timeout = timeout
        self._limits = limits
        self._retry = retry or RetryPolicy()
        self._rate = RateLimiter(rate=rate_per_second, burst=burst)
        self._circuits: dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        self._metrics = ScraperMetrics(source)
        self._base_headers = {
            "User-Agent": _USER_AGENTS[0],
            "Accept": "application/json, text/html, */*",
            "Accept-Encoding": "gzip, deflate, br",
            **(headers or {}),
        }
        self._follow_redirects = follow_redirects
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            limits=self._limits,
            headers=self._base_headers,
            follow_redirects=self._follow_redirects,
            http2=False,          # BZP/TED don't support h2 reliably
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc

    def _rotate_ua(self) -> str:
        return random.choice(_USER_AGENTS)

    async def request(
        self,
        method: str,
        url: str,
        *,
        timeout: httpx.Timeout | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        assert self._client is not None, "Use as async context manager"
        domain = self._domain(url)
        circuit = self._circuits[domain]
        retry = self._retry
        last_exc: BaseException | None = None

        for attempt in range(1, retry.max_attempts + 1):
            # Circuit breaker check
            if not circuit.allow_request():
                self._metrics.record_circuit_block()
                raise httpx.ConnectError(f"Circuit OPEN for {domain}")

            # Rate limit
            await self._rate.acquire(domain)

            # Rotate UA on retries
            if attempt > 1:
                kwargs.setdefault("headers", {})
                kwargs["headers"]["User-Agent"] = self._rotate_ua()

            t0 = time.monotonic()
            try:
                resp = await self._client.request(
                    method, url,
                    timeout=timeout or self._timeout,
                    **kwargs,
                )
                latency = (time.monotonic() - t0) * 1000
                self._metrics.record_items(bytes_dl=len(resp.content))

                if resp.status_code in RETRYABLE_STATUS and attempt < retry.max_attempts:
                    delay = retry.delay_for(attempt)
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", delay))
                        delay = min(retry_after, retry.max_delay)
                    logger.warning(
                        "source=%s attempt=%d/%d status=%d url=%s retry_in=%.1fs",
                        self._source, attempt, retry.max_attempts,
                        resp.status_code, url[:80], delay,
                    )
                    self._metrics.record_request(ok=False, latency_ms=latency, retried=True)
                    circuit.record_failure()
                    await asyncio.sleep(delay)
                    continue

                ok = resp.status_code < 400
                circuit.record_success() if ok else circuit.record_failure()
                self._metrics.record_request(ok=ok, latency_ms=latency, retried=attempt > 1)

                logger.debug(
                    "source=%s method=%s status=%d latency=%.0fms url=%s",
                    self._source, method, resp.status_code, latency, url[:80],
                )
                return resp

            except RETRYABLE_EXCEPTIONS as exc:
                latency = (time.monotonic() - t0) * 1000
                last_exc = exc
                circuit.record_failure()
                self._metrics.record_request(ok=False, latency_ms=latency, retried=attempt > 1)
                if attempt < retry.max_attempts:
                    delay = retry.delay_for(attempt)
                    logger.warning(
                        "source=%s attempt=%d/%d exc=%s url=%s retry_in=%.1fs",
                        self._source, attempt, retry.max_attempts,
                        type(exc).__name__, url[:80], delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        # Exhausted retries
        if last_exc:
            raise last_exc
        raise httpx.HTTPStatusError(
            f"Max retries exceeded for {url}",
            request=httpx.Request(method, url),
            response=httpx.Response(500),
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    @property
    def metrics(self) -> ScraperMetrics:
        return self._metrics


# ---------------------------------------------------------------------------
# ScraperBase ABC
# ---------------------------------------------------------------------------

class ScraperBase(ABC):
    """Abstract base for all terra-os ingestion scrapers.

    Subclass and implement `run_async()`. The context manager manages
    the HTTP client lifecycle.

    Class attributes:
        SOURCE       : str — metric/log label  (required)
        RATE         : float — requests/second (default 2.0)
        BURST        : int — token-bucket burst (default 5)
        RETRY        : RetryPolicy | None
        TIMEOUT      : httpx.Timeout | None
    """

    SOURCE: ClassVar[str] = "unknown"
    RATE: ClassVar[float] = 2.0
    BURST: ClassVar[int] = 5
    RETRY: ClassVar[RetryPolicy | None] = None
    TIMEOUT: ClassVar[httpx.Timeout] = DEFAULT_TIMEOUT

    def __init__(self, extra_headers: dict[str, str] | None = None):
        self._http: AsyncHTTPClient | None = None
        self._extra_headers = extra_headers or {}

    async def __aenter__(self) -> "ScraperBase":
        self._http = AsyncHTTPClient(
            source=self.SOURCE,
            timeout=self.TIMEOUT,
            retry=self.RETRY or RetryPolicy(),
            rate_per_second=self.RATE,
            burst=self.BURST,
            headers=self._extra_headers,
        )
        await self._http.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.__aexit__(*args)

    @property
    def http(self) -> AsyncHTTPClient:
        assert self._http is not None, "Use as async context manager"
        return self._http

    @property
    def metrics(self) -> ScraperMetrics:
        return self.http.metrics

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.http.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.http.post(url, **kwargs)

    @abstractmethod
    async def run_async(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the scrape job. Return summary dict."""
        ...

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Sync wrapper for run_async — for CLI / non-async callers."""
        return asyncio.run(self._run_with_ctx(**kwargs))

    async def _run_with_ctx(self, **kwargs: Any) -> dict[str, Any]:
        async with self:
            return await self.run_async(**kwargs)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def parse_pln(value: Any) -> float | None:
    """Parse Polish numeric string → float PLN.  '1 234 567,89 zł' → 1234567.89"""
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").replace(" ", "").replace(",", ".").replace("zł", "").strip()
    # Remove any non-numeric except dot/minus
    import re
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def normalize_cpv(cpv: str | None) -> str | None:
    """'45111200-0' → '45111200', handles various input formats."""
    if not cpv:
        return None
    import re
    m = re.search(r"(\d{8})", str(cpv))
    return m.group(1) if m else None


def safe_date(s: Any) -> str | None:
    """Parse date string to ISO8601, returns None on failure."""
    if not s:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d",
                "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s)[:19], fmt).isoformat()
        except ValueError:
            continue
    return str(s)[:32]
