"""Sadler's Wells — generic `a[href*="/whats-on/"]` matched the "Get tickets"
link inside each card. New adapter walks `.c-event-card` and reads:

  <a class="c-event-card__cover-link" href="https://.../whats-on/<slug>/">
    <span class="u-hidden-visually">Title</span>           ← title here
  </a>
  <figure class="c-event-card__image"><img src="..." /></figure>
  <h3 class="c-event-card__title">Title</h3>               ← also here (visible)
  <time class="c-event-card__daterange">12 – 30 May 2026</time>
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text


@register
class SadlersWellsAdapter(BaseAdapter):
    slug = "sadlers-wells"
    url = "https://www.sadlerswells.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".c-event-card"):
            link_el = card.css("a.c-event-card__cover-link").first
            title_el = card.css(".c-event-card__title").first
            if link_el is None or title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            date_el = card.css(".c-event-card__daterange").first
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
