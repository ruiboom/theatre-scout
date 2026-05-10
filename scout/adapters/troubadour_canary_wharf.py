"""Troubadour Canary Wharf Theatre — see `_troubadour.py` for the shared
Troubadour Theatres listing parser.
"""

from __future__ import annotations

from scout.adapters._troubadour import parse_troubadour
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class TroubadourCanaryWharfAdapter(BaseAdapter):
    slug = "troubadour-canary-wharf"
    url = "https://www.troubadourtheatres.com/canary-wharf-theatre"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_troubadour(html, base_url, theatre_slug=self.slug)
