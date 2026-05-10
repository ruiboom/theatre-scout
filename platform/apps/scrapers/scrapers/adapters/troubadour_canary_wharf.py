"""Troubadour Canary Wharf Theatre — see `_troubadour.py` for the shared
Troubadour Theatres listing parser.
"""

from __future__ import annotations

from ..models import Show
from ._troubadour import parse_troubadour
from .base import BaseAdapter
from .registry import register


@register
class TroubadourCanaryWharfAdapter(BaseAdapter):
    slug = "troubadour-canary-wharf"
    url = "https://www.troubadourtheatres.com/canary-wharf-theatre"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_troubadour(html, base_url, theatre_slug=self.slug)
