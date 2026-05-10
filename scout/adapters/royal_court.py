"""Royal Court — generic `a[href*="/events/"]` matched the "More info" link
text inside each card, so titles came back as e.g. "More info Krapp's Last
Tape...". Cards use the shared Spektrix Vue.js c-media markup; the canonical
URL only appears in the wrapper's `@click="goToUrl('https://...')"`.
"""

from __future__ import annotations

from scout.adapters._c_media import parse_c_media
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class RoyalCourtAdapter(BaseAdapter):
    slug = "royal-court"
    url = "https://royalcourttheatre.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
