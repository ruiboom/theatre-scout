"""Bulk-registered adapters using the GenericAdapter pattern.

Each entry: (slug, listings URL, card selector). The selector was discovered by
inspecting a saved fixture; bespoke parsing lives in its own module.

Slugs in `_JS_VENUES` route through the stealth (browser-rendered) fetch path
because the listing page is either JavaScript-rendered or the venue blocks
plain HTTP requests.

This module starts small. As scout/'s adapters are ported across, add their
entries here (or graduate to a bespoke module). See scout/adapters/bulk.py for
the full reference.
"""

from __future__ import annotations

from ._generic import GenericAdapter
from .registry import register

# Venues that need a real browser to render content (or to defeat anti-bot blocking).
_JS_VENUES: set[str] = set()

# (slug, url, selector). slug == key in theatres.yaml.
_ENTRIES: list[tuple[str, str, str]] = [
    # Seed with a couple of representative entries; expand when porting from scout.
    # ("bridge-theatre", "https://www.bridgetheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    # ("bush-theatre",   "https://www.bushtheatre.co.uk/whats-on/",   'a[href*="/event/"]'),
]


def _make_adapter(slug: str, url: str, card_selector: str) -> type[GenericAdapter]:
    cls_name = "".join(p.title() for p in slug.split("-")) + "Adapter"
    cls = type(
        cls_name,
        (GenericAdapter,),
        {
            "slug": slug,
            "url": url,
            "card_selector": card_selector,
            "requires_js": slug in _JS_VENUES,
        },
    )
    return cls


def load() -> None:
    """Register every entry in the module. Called once from `adapters/__init__.py`."""
    for slug, url, sel in _ENTRIES:
        register(_make_adapter(slug, url, sel))
