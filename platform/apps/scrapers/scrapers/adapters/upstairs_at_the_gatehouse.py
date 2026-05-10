"""Upstairs at the Gatehouse — listing now lives on Ticketsolve.

The venue's `/whats-on/` page 404s; the nav link points to the Ticketsolve
subdomain which renders shows behind a SPA, so we hit the Ticketsolve URL
directly with stealth (browser).
"""

from __future__ import annotations

from typing import Any

from ..models import Show
from ._ticketsolve import enrich_ticketsolve, parse_ticketsolve
from .base import BaseAdapter
from .registry import register


@register
class UpstairsAtTheGatehouseAdapter(BaseAdapter):
    slug = "upstairs-at-the-gatehouse"
    url = "https://upstairsatthegatehouse.ticketsolve.com/shows"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_ticketsolve(html, base_url, theatre_slug=self.slug)

    def enrich(self, html: str, base_url: str) -> dict[str, Any]:
        return enrich_ticketsolve(html, base_url)
