"""Courtyard Theatre, Hoxton. The Divi-built /whats-on/ page renders show
detail client-side, but every production still surfaces as a See Tickets
"Buy Now" link: `…seetickets.com/event/<slug>/the-courtyard-theatre/<id>`.
We derive the title from the URL slug and keep the See Tickets link as the
canonical (bookable) URL, deduping the multiple per-performance ids that point
at the same production.
"""

from __future__ import annotations

import re

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show

_EVENT_RE = re.compile(
    r"seetickets\.com/event/([a-z0-9-]+)/the-courtyard-theatre/\d+", re.IGNORECASE
)


@register
class CourtyardAdapter(BaseAdapter):
    slug = "courtyard"
    url = "https://thecourtyard.org.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[href*="seetickets.com/event/"]'):
            href = str(a.attrib.get("href", ""))
            m = _EVENT_RE.search(href)
            if m is None:
                continue
            slug = m.group(1)
            if slug in seen:
                continue
            # `alex-kealy-special-recording` -> `Alex Kealy Special Recording`.
            title = slug.replace("-", " ").title()
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        # Mixed music/comedy/theatre programme — don't assume.
                        show_type=classify(title, default="other"),
                        url=href.split("?", 1)[0],
                    )
                )
                seen.add(slug)
            except Exception:
                continue
        return shows
