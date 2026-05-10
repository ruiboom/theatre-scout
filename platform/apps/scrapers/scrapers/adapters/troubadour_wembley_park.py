"""Troubadour Wembley Park Theatre — uses the shared Troubadour Theatres
helper since the URL group lives at troubadourtheatres.com (the previous
`troubadour.com/wembley-park` URL is for an unrelated LA venue and 404s).
"""

from __future__ import annotations

from ..models import Show
from ._troubadour import parse_troubadour
from .base import BaseAdapter
from .registry import register


@register
class TroubadourWembleyParkAdapter(BaseAdapter):
    slug = "troubadour-wembley-park"
    url = "https://www.troubadourtheatres.com/wembley-park-theatre"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_troubadour(html, base_url, theatre_slug=self.slug)
