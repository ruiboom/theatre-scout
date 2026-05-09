"""Polite HTTP client. Backed by Scrapling sessions:

- A `FetcherSession` (curl_cffi + Chrome TLS) for the fast path. Connection-pooled.
- A `StealthySession` (Patchright headless browser) for the stealth path. Browser
  is launched once per Client and reused across stealth venues.

Both sessions are lazy-initialised; a `Client` that never sees a stealth call
never launches a browser. Always use `Client` as a context manager (or call
`close()` explicitly) so the underlying connections / browser shut down cleanly.

Public surface (kept stable so adapters and tests don't shift):
    Response          — frozen dataclass with .url / .status_code / .content / .text
    RateLimiter       — per-host token bucket
    is_allowed        — robots.txt check helper
    Client            — Client.get(url, *, stealth=False) -> Response | None
    USER_AGENT        — informational identifier we report in robots.txt rules
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.parse
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any

USER_AGENT = "TheatreScout/0.1 (+local research bot)"

log = logging.getLogger(__name__)


class RateLimiter:
    """Per-host token bucket. Thread-safe: each host has its own lock so concurrent
    callers to the same host serialize, while callers to different hosts proceed
    in parallel. Sleeps just enough to keep `min_interval` between hits."""

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
        self._registry_lock = threading.Lock()
        self._host_locks: dict[str, threading.Lock] = {}

    def _lock_for(self, host: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._host_locks.get(host)
            if lock is None:
                lock = threading.Lock()
                self._host_locks[host] = lock
            return lock

    def wait_for(self, host: str) -> None:
        with self._lock_for(host):
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
        self._user_agent = user_agent
        self._robots_cache: dict[str, str | None] = {}
        # Test injection points; if not provided, lazy-init Scrapling sessions.
        self._fetch_fn_override = fetch_fn
        self._stealth_fetch_fn_override = stealth_fetch_fn
        self._fetch_robots_override = fetch_robots
        # Each tuple is (entered_handle, context_manager) so we can call __exit__
        # on the original CM while using the entered handle for requests.
        self._fetcher_session: tuple[Any, Any] | None = None
        self._stealth_session: tuple[Any, Any] | None = None

    # ---- context manager so sessions get closed cleanly ----
    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._fetcher_session is not None:
            _, cm = self._fetcher_session
            try:
                cm.__exit__(None, None, None)
            except Exception as e:
                log.warning("error closing fetcher session: %s", e)
            self._fetcher_session = None
        if self._stealth_session is not None:
            _, cm = self._stealth_session
            try:
                cm.__exit__(None, None, None)
            except Exception as e:
                log.warning("error closing stealth session: %s", e)
            self._stealth_session = None

    # ---- public API ----
    def get(self, url: str, *, stealth: bool = False) -> Response | None:
        host = urllib.parse.urlparse(url).netloc
        if not self._is_allowed(url, host):
            return None
        self._rate.wait_for(host)
        return self._stealth_fetch(url) if stealth else self._fetch(url)

    # ---- internals ----
    def _fetch(self, url: str) -> Response | None:
        if self._fetch_fn_override is not None:
            return self._fetch_fn_override(url)
        try:
            page = self._fetcher().get(url, stealthy_headers=True, timeout=20)
        except Exception as exc:
            log.warning("fetch failed for %s: %s", url, exc)
            return None
        return _to_response(page)

    def _stealth_fetch(self, url: str) -> Response | None:
        if self._stealth_fetch_fn_override is not None:
            return self._stealth_fetch_fn_override(url)
        try:
            page = self._stealth().fetch(url)
        except Exception as exc:
            log.warning("stealth fetch failed for %s: %s", url, exc)
            return None
        return _to_response(page)

    def _fetcher(self) -> Any:
        if self._fetcher_session is None:
            from scrapling.fetchers import FetcherSession

            cm = FetcherSession(impersonate="chrome", stealthy_headers=True, timeout=20, retries=2)
            handle = cm.__enter__()
            self._fetcher_session = (handle, cm)
        return self._fetcher_session[0]

    def _stealth(self) -> Any:
        if self._stealth_session is None:
            from scrapling.fetchers import StealthySession

            cm = StealthySession(
                headless=True,
                disable_resources=True,
                network_idle=True,
                timeout=45000,
            )
            handle = cm.__enter__()  # type: ignore[no-untyped-call]
            self._stealth_session = (handle, cm)
        return self._stealth_session[0]

    def _is_allowed(self, url: str, host: str) -> bool:
        if host not in self._robots_cache:
            try:
                self._robots_cache[host] = self._robots_for(host)
            except Exception:
                self._robots_cache[host] = None
        return is_allowed(url, self._robots_cache[host], user_agent=self._user_agent)

    def _robots_for(self, host: str) -> str | None:
        if self._fetch_robots_override is not None:
            return self._fetch_robots_override(host)
        resp = self._fetch(f"https://{host}/robots.txt")
        if resp is None or resp.status_code != 200:
            return None
        return resp.text


def _to_response(page: Any) -> Response:
    body = page.body if isinstance(page.body, bytes) else str(page).encode("utf-8")
    return Response(url=str(page.url), status_code=int(page.status), content=body)
