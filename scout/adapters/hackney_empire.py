"""Hackney Empire — generic `a[href*="/events/"]` was grabbing the "Details"
button text per card. Cards use the shared Spektrix c-media markup with a
static `<a href="/events/<slug>">` so the helper picks it up cleanly.
"""

from __future__ import annotations

from scout.adapters._c_media import parse_c_media
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class HackneyEmpireAdapter(BaseAdapter):
    slug = "hackney-empire"
    url = "https://www.hackneyempire.co.uk/whats-on"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
