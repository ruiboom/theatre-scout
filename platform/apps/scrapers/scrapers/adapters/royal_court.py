"""Royal Court — generic `a[href*="/events/"]` matched the "More info" link
text inside each card, so titles came back as e.g. "More info Krapp's Last
Tape...". Cards use the shared Spektrix Vue.js c-media markup; the canonical
URL only appears in the wrapper's `@click="goToUrl('https://...')"`.
"""

from __future__ import annotations

from ..models import Show
from ._c_media import parse_c_media
from .base import BaseAdapter, _ClientLike
from .registry import register


@register
class RoyalCourtAdapter(BaseAdapter):
    slug = "royal-court"
    url = "https://royalcourttheatre.com/whats-on/"
    requires_js = False  # see fetch(): stealth is forced for the listing only

    def fetch(self, client: _ClientLike) -> list[Show]:
        # 403'd from datacenter IPs (the daily cron) but fine from residential —
        # the venue's WAF blocks the runner's IP range. Route the listing through
        # the stealth browser to try to get past it; requires_js stays False so
        # enrich doesn't stealth-render every show page. The @click="goToUrl()"
        # URLs parse_c_media needs survive rendering (verified vs the static HTML).
        text = self._response_text(client.get(self.url, stealth=True))
        return self.parse(text, self.url)

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_c_media(html, base_url, theatre_slug=self.slug)
