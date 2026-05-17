"""The Hope Theatre, Islington — 50-seat pub theatre on a Wix site. The
/what-s-on page renders client-side, so we fetch with the stealth browser and
use the shared JS-listings helper (JSON-LD, then Wix `/event-details/`
anchors, with an image-`alt` fallback for Pro Gallery layouts). Best-effort.

Mirrors scout/adapters/hope_theatre.py.
"""

from __future__ import annotations

from ..models import Show
from ._jslisting import parse_js_listings
from .base import BaseAdapter
from .registry import register


@register
class HopeTheatreAdapter(BaseAdapter):
    slug = "hope-theatre"
    url = "https://www.thehopetheatre.com/what-s-on"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(
            html, base_url, self.slug, href_contains=("/event-details/", "/what-s-on/")
        )
