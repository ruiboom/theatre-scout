"""Charing Cross Theatre — the homepage doesn't have a card grid; only the
WHAT'S ON dropdown menu lists current productions. The site runs at most a
handful of shows at a time, each linked as `<a href="theatre/<slug>">Title</a>`.

This adapter parses the dropdown directly. Filters out the "Calendar View"
nav item and any other non-show entries.
"""

from __future__ import annotations

import re
import urllib.parse

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

_NON_SHOW_SLUGS = {
    "calendar",
    "calendar-view",
    "archive",
    "show-archive",
    "history",
}
# Loose sanity check on what a real production slug looks like — letters,
# numbers, dashes, sometimes a year suffix.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")


@register
class CharingCrossAdapter(BaseAdapter):
    slug = "charing-cross"
    url = "https://charingcrosstheatre.co.uk/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[href*="theatre/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href:
                continue
            slug = href.rsplit("/", 1)[-1]
            if not _SLUG_RE.match(slug) or slug in _NON_SHOW_SLUGS:
                continue
            title = clean_text(a.get_all_text(separator=" ", strip=True))
            if not title or title.lower() in {"calendar", "calendar view", "show archive"}:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
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
