"""Polite HTTP client. Internally delegates to Scrapling so we get TLS impersonation
on the fast path and Patchright-based browser rendering on the stealth path —
without changing the adapter contract.

Public surface (kept intentionally stable so adapters and tests don't shift):
    Response          — frozen dataclass with .url / .status_code / .content / .text
    RateLimiter       — per-host token bucket
    is_allowed        — robots.txt check helper
    Client            — Client.get(url, *, stealth=False) -> Response | None
    USER_AGENT        — informational identifier we report in robots.txt rules
"""

from __future__ import annotations

import logging
import time
import urllib.parse
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass

USER_AGENT = "TheatreScout/0.1 (+local research bot)"

log = logging.getLogger(__name__)


class RateLimiter:
    """Per-host token bucket. Sleeps just enough to keep `min_interval` between hits."""

    def __init__(
        self,
        *,
        min_interval: float = 1.0,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._now = now
        self._sleep = sleep
        self._last_at: dict[str, float] = {}

    def wait_for(self, host: str) -> None:
        last = self._last_at.get(host)
        if last is not None:
            wait = self._min_interval - (self._now() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_at[host] = self._now()


def is_allowed(url: str, robots_txt: str | None, *, user_agent: str = USER_AGENT) -> bool:
    if not robots_txt:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return parser.can_fetch(user_agent, url)


@dataclass(frozen=True)
class Response:
    url: str
    status_code: int
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


FetchFn = Callable[[str], Response | None]


def _scrapling_fetch(url: str) -> Response | None:
    """Default fast-path fetch via Scrapling's curl_cffi-based Fetcher (Chrome TLS)."""
    from scrapling.fetchers import Fetcher

    try:
        page = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=20)
    except Exception as exc:
        log.warning("fetch failed for %s: %s", url, exc)
        return None
    body = page.body if isinstance(page.body, bytes) else str(page).encode("utf-8")
    return Response(url=str(page.url), status_code=int(page.status), content=body)


def _scrapling_stealth_fetch(url: str) -> Response | None:
    """Slow-path fetch via Scrapling's StealthyFetcher (Patchright headless browser)."""
    from scrapling.fetchers import StealthyFetcher

    try:
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            disable_resources=True,
            network_idle=True,
            timeout=45000,
        )
    except Exception as exc:
        log.warning("stealth fetch failed for %s: %s", url, exc)
        return None
    body = page.body if isinstance(page.body, bytes) else str(page).encode("utf-8")
    return Response(url=str(page.url), status_code=int(page.status), content=body)


def _scrapling_robots_fetch(host: str) -> str | None:
    """Pull /robots.txt for a host using the fast-path fetcher."""
    resp = _scrapling_fetch(f"https://{host}/robots.txt")
    if resp is None or resp.status_code != 200:
        return None
    return resp.text


class Client:
    """Polite client: rate-limited, robots-aware, with optional stealth escalation."""

    def __init__(
        self,
        *,
        rate_limiter: RateLimiter | None = None,
        fetch_fn: FetchFn | None = None,
        stealth_fetch_fn: FetchFn | None = None,
        fetch_robots: Callable[[str], str | None] | None = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._rate = rate_limiter or RateLimiter()
        self._fetch_fn = fetch_fn or _scrapling_fetch
        self._stealth_fetch_fn = stealth_fetch_fn or _scrapling_stealth_fetch
        self._fetch_robots = fetch_robots or _scrapling_robots_fetch
        self._user_agent = user_agent
        self._robots_cache: dict[str, str | None] = {}

    def get(self, url: str, *, stealth: bool = False) -> Response | None:
        host = urllib.parse.urlparse(url).netloc
        if not self._is_allowed(url, host):
            return None
        self._rate.wait_for(host)
        fetch = self._stealth_fetch_fn if stealth else self._fetch_fn
        return fetch(url)

    def _is_allowed(self, url: str, host: str) -> bool:
        if host not in self._robots_cache:
            try:
                self._robots_cache[host] = self._fetch_robots(host)
            except Exception:
                self._robots_cache[host] = None
        return is_allowed(url, self._robots_cache[host], user_agent=self._user_agent)
