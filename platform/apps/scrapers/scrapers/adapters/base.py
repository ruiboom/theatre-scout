"""BaseAdapter — one subclass per venue. Mirrors scout/adapters/base.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from ..models import Show


class _ClientLike(Protocol):
    def get(self, url: str, *, stealth: bool = False) -> object | None: ...


class FetchError(RuntimeError):
    """The listing fetch did not yield a usable page.

    Raised for a missing response (network error / timeout / robots-disallowed,
    all surfaced by `client.get` as None) or an HTTP error status (>= 400 — e.g.
    a 503 maintenance page or a 403 anti-bot block). The orchestrator catches it
    and records a `failed` ScrapeRun, so a fetch failure is no longer recorded as
    a successful scrape that happened to find nothing — a "silent zero" that the
    venue-health monitor couldn't tell apart from a genuinely empty listing.
    """


class BaseAdapter(ABC):
    """Per-theatre adapter. Subclasses must define `slug`, `url`, and `parse(html, base_url)`.

    Adapters are pure functions of `(html, base_url) -> list[Show]`. The orchestrator
    handles the HTTP fetch (rate-limiting, stealth dispatch, retry policy). Keeping
    parse() pure means `tests/adapters/test_<slug>.py` can run from a saved HTML
    fixture without network.
    """

    #: Kebab-case slug matching `theatres.yaml`. The orchestrator uses this to look
    #: up the venue row when writing.
    slug: str = ""

    #: Listings URL the orchestrator passes to `client.get()`.
    url: str = ""

    #: True when the listings page is JS-rendered (or actively blocks plain HTTP).
    #: The orchestrator routes these via the stealth (Patchright) path.
    requires_js: bool = False

    @abstractmethod
    def parse(self, html: str, base_url: str) -> list[Show]:
        """Pure parser: HTML → list of Show. No IO."""

    def enrich(self, html: str, base_url: str) -> dict[str, Any]:
        """Per-adapter detail-page extraction. Returns candidate field updates.

        Default uses the generic description and image extractors. Override when
        a venue exposes structured pricing or when the generic extractor misses
        content (e.g. pages with no `<main>`/`<article>` wrapper).

        Caller decides which fields to actually apply — see `runner._enrich`.
        """
        # Imported lazily so adapters don't carry the enrich import at module load.
        from ..enrich import extract_description, extract_image

        out: dict[str, Any] = {}
        desc = extract_description(html)
        if desc:
            out["description"] = desc
        img = extract_image(html, base_url)
        if img:
            out["image_url"] = img
        return out

    def fetch(self, client: _ClientLike) -> list[Show]:
        text = self._response_text(client.get(self.url, stealth=self.requires_js))
        return self.parse(text, self.url)

    def _response_text(self, resp: object | None, *, url: str | None = None) -> str:
        """Validate a fetch response and return its decoded body.

        Raises `FetchError` on a missing response (None) or an HTTP error status
        (>= 400). Shared by every `fetch()` — including the stealth-forcing and
        multi-hop overrides — so a dead fetch raises everywhere instead of
        silently returning `[]`. `url` overrides the URL named in the error (for
        multi-hop adapters that fetch something other than `self.url`).
        """
        where = url or self.url
        if resp is None:
            raise FetchError(f"no response for {where} (fetch failed or robots-disallowed)")
        status = getattr(resp, "status_code", None)
        if status is not None and status >= 400:
            raise FetchError(f"HTTP {status} for {where}")
        return getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
            "utf-8", errors="replace"
        )
