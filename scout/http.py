from __future__ import annotations

import hashlib
import time
import urllib.parse
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

USER_AGENT = "TheatreScout/0.1 (+local research bot)"


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


class Cache:
    """File-backed bytes cache keyed by URL hash. No TTL — fixtures are stable in dev."""

    def __init__(self, dir: Path) -> None:
        self._dir = Path(dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        h = hashlib.sha256(url.encode()).hexdigest()
        return self._dir / f"{h}.bin"

    def get(self, url: str) -> bytes | None:
        p = self._path(url)
        return p.read_bytes() if p.is_file() else None

    def put(self, url: str, content: bytes) -> None:
        self._path(url).write_bytes(content)


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


class Client:
    """Polite HTTP client: rate-limited, cached, robots-aware."""

    def __init__(
        self,
        *,
        http: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        cache: Cache | None = None,
        fetch_robots: Callable[[str], str | None] | None = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._http = http or httpx.Client(timeout=20.0, follow_redirects=True)
        self._http.headers["user-agent"] = user_agent
        self._rate = rate_limiter or RateLimiter()
        self._cache = cache
        self._fetch_robots = fetch_robots or _live_robots_fetcher(self._http)
        self._user_agent = user_agent
        self._robots_cache: dict[str, str | None] = {}

    def get(self, url: str) -> Response | None:
        host = urllib.parse.urlparse(url).netloc
        if not self._is_allowed(url, host):
            return None
        if self._cache is not None and (cached := self._cache.get(url)) is not None:
            return Response(url=url, status_code=200, content=cached)
        self._rate.wait_for(host)
        resp = self._http.get(url)
        if resp.status_code == 200 and self._cache is not None:
            self._cache.put(url, resp.content)
        return Response(url=url, status_code=resp.status_code, content=resp.content)

    def _is_allowed(self, url: str, host: str) -> bool:
        if host not in self._robots_cache:
            try:
                self._robots_cache[host] = self._fetch_robots(host)
            except Exception:
                self._robots_cache[host] = None
        return is_allowed(url, self._robots_cache[host], user_agent=self._user_agent)


def _live_robots_fetcher(http: httpx.Client) -> Callable[[str], str | None]:
    def fetch(host: str) -> str | None:
        try:
            r = http.get(f"https://{host}/robots.txt")
            return r.text if r.status_code == 200 else None
        except Exception:
            return None

    return fetch
