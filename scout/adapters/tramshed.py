"""Tramshed, Woolwich — comedy & music venue on a Wix site that sells through
Ticket Tailor. The /whatson page renders client-side, so we fetch with the
stealth browser and use the shared JS-listings helper, accepting both Wix
`/event-details/` and Ticket Tailor links. Comedy-leaning programme, so that
is the classification fallback. Best-effort.
"""

from __future__ import annotations

from scout.adapters._jslisting import parse_js_listings
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class TramshedAdapter(BaseAdapter):
    slug = "tramshed"
    url = "https://www.tramshed.org/whatson"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(
            html,
            base_url,
            self.slug,
            default_type="comedy",
            href_contains=("/event-details/", "tickettailor.com"),
        )
