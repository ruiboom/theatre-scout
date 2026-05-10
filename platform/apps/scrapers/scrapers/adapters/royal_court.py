"""Royal Court — generic `a[href*="/events/"]` matched the "More info" link
text inside each card, so titles came back as e.g. "More info Krapp's Last
Tape...". Cards use the shared Spektrix Vue.js c-media markup; the canonical
URL only appears in the wrapper's `@click="goToUrl('https://...')"`.
"""

from __future__ import annotations

from ..models import Show
from ._c_media import parse_c_media
from .base import BaseAdapter
from .registry import register


@register
class RoyalCourtAdapter(BaseAdapter):
    slug = "royal-court"
    url = "https://royalcourttheatre.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
