"""Tramshed, Woolwich — comedy & music venue on a Wix site that sells through
Ticket Tailor. The /whatson page renders client-side, so we fetch with the
stealth browser and use the shared JS-listings helper, accepting both Wix
`/event-details/` and Ticket Tailor links. Comedy-leaning programme, so that
is the classification fallback. Best-effort.

Mirrors scout/adapters/tramshed.py.
"""

from __future__ import annotations

from ..models import Show
from ._jslisting import parse_js_listings
from .base import BaseAdapter
from .registry import register


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
