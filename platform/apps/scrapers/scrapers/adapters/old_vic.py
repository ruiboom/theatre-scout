"""Old Vic — generic `a[href*="/productions/"]` matched the page-header link
"Productions" so every row came back titled "Productions". The actual title
sits inside a `<div class="sr-only">` (screen-reader-only fallback) because
the visible card is just a stylised SVG poster with the title rendered as
graphics. New adapter walks `a.poster-card` anchors and pulls:

  <a href="/stage/<slug>/" class="poster-card">
    <div class="poster"><img src="..." /></div>
    <div class="sr-only">One Flew Over the Cuckoo's Nest</div>   ← title
  </a>
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter
from .registry import register


@register
class OldVicAdapter(BaseAdapter):
    slug = "old-vic"
    url = "https://www.oldvictheatre.com/productions/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css("a.poster-card"):
            href = str(card.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            sr_el = card.css(".sr-only").first
            if sr_el is None or not href:
                continue
            title = clean_text(sr_el.get_all_text(separator=" ", strip=True))
            if not title:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            img_el = card.css(".poster img").first
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
                        image_url=image_url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows
