"""Richmond Theatre — uses the shared ATG parser; see `_atg.py`."""

from __future__ import annotations

from scout.adapters._atg import parse_atg
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class RichmondAdapter(BaseAdapter):
    slug = "richmond"
    url = "https://www.atgtickets.com/venues/richmond-theatre/whats-on/"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_atg(html, base_url, theatre_slug=self.slug, venue_slug="richmond-theatre")
