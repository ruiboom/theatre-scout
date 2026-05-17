"""Barons Court Theatre — hand-built Wix site (JS-rendered, so requires_js).

The programme lives at /upcoming-performances, where each production is a
`<a data-testid="linkElement" href="https://www.baronscourttheatre.com/<slug>">`
whose link text is the show title. Wix auto-generates CSS class hashes, so we
anchor on the stable `data-testid` + the venue's own per-show URLs, filtering
out the fixed set of nav/utility pages.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

# Non-show pages reachable from the same `linkElement` anchors.
_NAV = {
    "",
    "about",
    "box-office",
    "contact",
    "home",
    "opportunities",
    "pastproductions",
    "submissions",
    "upcoming-performances",
}


@register
class BaronsCourtAdapter(BaseAdapter):
    slug = "barons-court"
    url = "https://www.baronscourttheatre.com/upcoming-performances"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[data-testid="linkElement"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if "baronscourttheatre.com/" not in href:
                continue
            path = urllib.parse.urlparse(href).path.strip("/")
            if not path or "/" in path or path.lower() in _NAV:
                continue
            url = f"https://www.baronscourttheatre.com/{path}"
            if url in seen:
                continue
            title = clean_text(a.get_all_text(separator=" ", strip=True))
            if not title or len(title) > 200:
                continue
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows
