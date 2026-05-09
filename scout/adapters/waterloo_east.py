"""Waterloo East Theatre — listing lives on Ticketsolve.

The venue homepage exposes a "Book Online" button that links to its Ticketsolve
subdomain; that subdomain is where the actual show grid renders (via JS).
"""

from __future__ import annotations

from typing import Any

from scout.adapters._ticketsolve import enrich_ticketsolve, parse_ticketsolve
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class WaterlooEastAdapter(BaseAdapter):
    slug = "waterloo-east"
    url = "https://waterlooeast.ticketsolve.com/shows"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_ticketsolve(html, base_url, theatre_slug=self.slug)

    def enrich(self, html: str, base_url: str) -> dict[str, Any]:
        return enrich_ticketsolve(html, base_url)
