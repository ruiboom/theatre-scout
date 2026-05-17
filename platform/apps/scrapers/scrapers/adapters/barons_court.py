"""Barons Court Theatre — Wix Events site. The programme is rendered
client-side (the static HTML only carries Wix system pages), so we fetch with
the stealth browser and lean on the shared JS-listings helper, which reads
JSON-LD or `/event-details/` anchors. Best-effort: yields what the render
exposes, [] otherwise.

Mirrors scout/adapters/barons_court.py.
"""

from __future__ import annotations

from ..models import Show
from ._jslisting import parse_js_listings
from .base import BaseAdapter
from .registry import register


@register
class BaronsCourtAdapter(BaseAdapter):
    slug = "barons-court"
    url = "https://www.baronscourttheatre.com/"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(html, base_url, self.slug)
