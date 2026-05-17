"""Bread & Roses Theatre, Clapham — fringe room above the Bread & Roses pub.
The site is a Jimdo builder whose /whats-on.html injects its programme
client-side (static HTML is navigation only), so we fetch with the stealth
browser and use the shared JS-listings helper. Best-effort: the rendered
structure is unverified, so this yields what it can and [] otherwise.

Mirrors scout/adapters/bread_and_roses.py.
"""

from __future__ import annotations

from ..models import Show
from ._jslisting import parse_js_listings
from .base import BaseAdapter
from .registry import register


@register
class BreadAndRosesAdapter(BaseAdapter):
    slug = "bread-and-roses"
    url = "https://www.breadandrosestheatre.co.uk/whats-on.html"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(
            html, base_url, self.slug, href_contains=("/whats-on", "/event", "/show")
        )
