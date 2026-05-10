"""Tower Theatre — generic `a[href*="/event/"]` matched both the card link and
the per-card "tribe-tickets" anchor, returning duplicate rows. The site also
hosts each show under its own slug at `/<slug>/` (no `/event/` segment), so
the URL pattern was wrong too.

New adapter walks `.new-grid-card` cards and reads:

  <a href="https://www.towertheatre.org.uk/<slug>/">
    <img class="homepage-event-card wp-post-image" src="..." />
    <h3 class="events-grid-title">Title</h3>
    <span class="date-description">Wednesday 13 – Saturday 23 May</span>
  </a>
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from ._html import parse_date_range
from .base import BaseAdapter
from .registry import register


@register
class TowerAdapter(BaseAdapter):
    slug = "tower"
    url = "https://www.towertheatre.org.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".new-grid-card"):
            link_el = card.css("a[href]").first
            title_el = card.css(".events-grid-title").first
            if link_el is None or title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            date_el = card.css(".date-description").first
            date_text = (
                clean_text(date_el.get_all_text(separator=" ", strip=True)) if date_el else ""
            )
            start, end = parse_date_range(date_text)

            img_el = card.css("img").first
            image_url: str | None = None
            if img_el is not None:
                src = img_el.attrib.get("src") or img_el.attrib.get("data-src")
                if isinstance(src, str) and src and not src.startswith("data:"):
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
                seen.add(url)
            except Exception:
                continue
        return shows
