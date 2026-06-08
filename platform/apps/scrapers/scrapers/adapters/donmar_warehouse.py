"""Donmar Warehouse — uses the shared Spektrix Vue.js c-media parser since the
generic adapter would pick up "Book now" / "More info" anchors as titles.

See `scout/adapters/_c_media.py` for the markup contract.
"""

from __future__ import annotations

from ..models import Show
from ._c_media import parse_c_media
from .base import BaseAdapter, _ClientLike
from .registry import register


@register
class DonmarWarehouseAdapter(BaseAdapter):
    slug = "donmar-warehouse"
    url = "https://www.donmarwarehouse.com/whats-on/"
    requires_js = False  # see fetch(): stealth is forced for the listing only

    def fetch(self, client: _ClientLike) -> list[Show]:
        # The fast HTTP path is 403'd from datacenter IPs (the daily GitHub
        # Actions cron) but works from residential ones — the venue's WAF blocks
        # the runner's IP range. Route the listing through the stealth browser to
        # try to get past it. requires_js stays False so the enrich phase doesn't
        # stealth-render every show page (the listing is the only blocked fetch),
        # and parse_c_media yields the same cards from rendered HTML as static.
        text = self._response_text(client.get(self.url, stealth=True))
        return self.parse(text, self.url)

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
