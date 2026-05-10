"""BaseAdapter — one subclass per venue. Mirrors scout/adapters/base.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from ..models import Show


class _ClientLike(Protocol):
    def get(self, url: str, *, stealth: bool = False) -> object | None: ...


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
        resp = client.get(self.url, stealth=self.requires_js)
        if resp is None:
            return []
        text = getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
            "utf-8", errors="replace"
        )
        return self.parse(text, self.url)
