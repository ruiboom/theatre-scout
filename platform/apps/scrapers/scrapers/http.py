"""
Shared HTTP client.

- 1 request / second per host (token bucket)
- Polite User-Agent
- Optional on-disk response cache for dev (set SCRAPER_CACHE=1)
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

import httpx

USER_AGENT = "AnywhereBuTheWestEnd/0.1 (+https://anywhere.example.com/bot)"
CACHE_DIR = Path(".cache/scraper")
CACHE_TTL_SEC = 60 * 60  # 1 hour


class _PerHostBucket:
    """1 request per second per host. Thread-safe."""

    def __init__(self, rate_per_sec: float = 1.0):
        self._interval = 1.0 / rate_per_sec
        self._last: dict[str, float] = defaultdict(float)
        self._lock = Lock()

    def wait_then_mark(self, host: str) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last[host]
            if elapsed < self._interval:
                time.sleep(self._interval - elapsed)
            self._last[host] = time.monotonic()


class Http:
    def __init__(self, *, cache: bool | None = None) -> None:
        self._cache = cache if cache is not None else os.getenv("SCRAPER_CACHE") == "1"
        self._buckets = _PerHostBucket()
        self._client = httpx.Client(
            headers={"user-agent": USER_AGENT},
            timeout=20.0,
            follow_redirects=True,
        )
        if self._cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> str:
        if self._cache:
            cached = self._read_cache(url)
            if cached is not None:
                return cached

        host = urlsplit(url).netloc
        self._buckets.wait_then_mark(host)

        resp = self._client.get(url)
        resp.raise_for_status()
        body = resp.text

        if self._cache:
            self._write_cache(url, body)
        return body

    def close(self) -> None:
        self._client.close()

    # ---- cache ----

    def _cache_path(self, url: str) -> Path:
        h = hashlib.sha256(url.encode()).hexdigest()[:24]
        return CACHE_DIR / f"{h}.html"

    def _read_cache(self, url: str) -> str | None:
        p = self._cache_path(url)
        if not p.exists():
            return None
        if (time.time() - p.stat().st_mtime) > CACHE_TTL_SEC:
            return None
        return p.read_text(encoding="utf-8")

    def _write_cache(self, url: str, body: str) -> None:
        self._cache_path(url).write_text(body, encoding="utf-8")
