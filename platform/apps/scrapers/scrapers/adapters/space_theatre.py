"""The Space, Isle of Dogs. space.org.uk sits behind Imperva/Incapsula bot
protection: plain HTTP returns only a JS challenge page. Crucially this is
*deliberately not* `requires_js` — the stealth browser was unreliable for the
previously-dropped Incapsula/anti-bot venues and cost minutes per scrape on
retries (see the note in adapters/bulk.py). Rather than burn that time every
run on a venue we can't currently reach, this adapter stays HTTP-only: it
parses real listings if the challenge is ever absent and yields [] otherwise.
The venue still appears in the directory. Revisit if Incapsula is lifted or a
reliable bypass lands.

Mirrors scout/adapters/space_theatre.py.
"""

from __future__ import annotations

from ..models import Show
from ._jslisting import parse_js_listings
from .base import BaseAdapter
from .registry import register


@register
class SpaceTheatreAdapter(BaseAdapter):
    slug = "space-theatre"
    url = "https://space.org.uk/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        return parse_js_listings(
            html, base_url, self.slug, href_contains=("/event", "/show", "/whats-on")
        )
