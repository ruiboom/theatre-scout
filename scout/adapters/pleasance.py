"""Pleasance Theatre London — bespoke because the listings page also includes
~250 Edinburgh Fringe shows alongside the actual London (Islington) programme.

Strategy:
  1. Find every `/event/X` link on the page.
  2. Filter to shows whose card text mentions "London" (Edinburgh shows say so explicitly).
  3. Strip the "Book tickets for" prefix from link text to get the real title.
  4. Group by canonical URL.
"""

from __future__ import annotations

import re
import urllib.parse

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show

_BOOK_TICKETS_RE = re.compile(r"^book tickets for\s+", re.IGNORECASE)
_LONDON_RE = re.compile(r"\bLondon\b")


@register
class PleasanceAdapter(BaseAdapter):
    slug = "pleasance"
    url = "https://www.pleasance.co.uk/events"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen_urls: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[href*="/event/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or href.endswith("/event/"):
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen_urls:
                continue

            parent = a.parent if a.parent is not None else a
            card_text = parent.get_all_text(separator=" ", strip=True)
            if not _LONDON_RE.search(card_text):
                continue  # Edinburgh-only or unmarked → skip

            link_text = a.get_all_text(separator=" ", strip=True)
            title = _BOOK_TICKETS_RE.sub("", link_text).strip()
            if not title or title.lower() in {"book now", "book tickets"}:
                continue

            start, end = parse_date_range(card_text)
            img = parent.css("img").first
            image_url: str | None = None
            if img is not None:
                src = img.attrib.get("src") or img.attrib.get("data-src")
                if isinstance(src, str) and src:
                    image_url = urllib.parse.urljoin(base_url, src)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=url,
                        start_date=start,
                        end_date=end,
                        image_url=image_url,
                    )
                )
                seen_urls.add(url)
            except Exception:
                continue
        return shows
