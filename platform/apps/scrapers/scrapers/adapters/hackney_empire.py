"""Hackney Empire — generic `a[href*="/events/"]` was grabbing the "Details"
button text per card. Cards use the shared Spektrix c-media markup with a
static `<a href="/events/<slug>">` so the helper picks it up cleanly.
"""

from __future__ import annotations

from ..models import Show
from ._c_media import parse_c_media
from .base import BaseAdapter
from .registry import register


@register
class HackneyEmpireAdapter(BaseAdapter):
    slug = "hackney-empire"
    url = "https://www.hackneyempire.co.uk/whats-on"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
