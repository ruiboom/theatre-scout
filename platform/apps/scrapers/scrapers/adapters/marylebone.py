"""Marylebone Theatre — generic `[class*=production-item]` selector matched
the wrapper but the title-extraction picked up the genre `<h3>` ("Theatre")
rather than the show `<h2>`. New adapter walks `.production-item` cards and
reads:

  <a class="production-image" href="/productions/<slug>"><img alt="Title"></a>
  <h3 class="genre">Theatre</h3>           ← genre, NOT title
  <h2 class="show-title">Title</h2>        ← title
  <div class="creatives"><p>By X / starring Y</p></div>
  <div class="date">...</div>              ← often "Dates to be confirmed"
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
class MaryleboneAdapter(BaseAdapter):
    slug = "marylebone"
    url = "https://www.marylebonetheatre.com/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".production-item"):
            title_el = card.css(".show-title").first
            link_el = card.css('a[href*="/productions/"]').first
            if title_el is None or link_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            creatives_el = card.css(".creatives").first
            description = (
                clean_text(creatives_el.get_all_text(separator=" ", strip=True))
                if creatives_el
                else ""
            )

            date_text = " ".join(
                clean_text(d.get_all_text(separator=" ", strip=True)) for d in card.css(".date")
            )
            start, end = parse_date_range(date_text)

            genre_el = card.css(".genre").first
            genre = genre_el.get_all_text(strip=True) if genre_el else ""

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
                        show_type=classify(f"{title} {description}", genre=genre),
                        url=url,
                        description=description,
                        start_date=start,
                        end_date=end,
                        image_url=image_url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows
