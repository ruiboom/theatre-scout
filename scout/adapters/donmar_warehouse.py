"""Donmar Warehouse — uses the shared Spektrix Vue.js c-media parser since the
generic adapter would pick up "Book now" / "More info" anchors as titles.

See `scout/adapters/_c_media.py` for the markup contract.
"""

from __future__ import annotations

from scout.adapters._c_media import parse_c_media
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class DonmarWarehouseAdapter(BaseAdapter):
    slug = "donmar-warehouse"
    url = "https://www.donmarwarehouse.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
