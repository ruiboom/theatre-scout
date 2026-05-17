"""Bread & Roses Theatre, Clapham — fringe room above the Bread & Roses pub.
The site is a Jimdo builder whose /whats-on.html injects its programme
client-side (static HTML is navigation only), so we fetch with the stealth
browser and use the shared JS-listings helper. Best-effort: the rendered
structure is unverified, so this yields what it can and [] otherwise.
"""

from __future__ import annotations

from scout.adapters._jslisting import parse_js_listings
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class BreadAndRosesAdapter(BaseAdapter):
    slug = "bread-and-roses"
    url = "https://www.breadandrosestheatre.co.uk/whats-on.html"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(
            html, base_url, self.slug, href_contains=("/whats-on", "/event", "/show")
        )
