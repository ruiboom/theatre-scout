"""Lyric Hammersmith — generic `a[href*="/shows/"]` matched the "More info"
anchor in each card and gave every row that title. New adapter walks WordPress
`<article class="card card--event">` cards and reads:

  <h4>Title</h4>                           inside .card__heading
  <p class="card__dates">07 May - 06 Jun 2026</p>
  <div class="card__summary">Synopsis...</div>
  <a class="card__fill-link" href="/shows/<slug>/">More info</a>
  <span class="category">Comedy</span>     in .card__categories
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
class LyricHammersmithAdapter(BaseAdapter):
    slug = "lyric-hammersmith"
    url = "https://lyric.co.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css("article.card--event"):
            heading = card.css(".card__heading").first
            link_el = card.css('a.card__fill-link, a[href*="/shows/"]').first
            if heading is None or link_el is None:
                continue
            title = clean_text(heading.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            dates_el = card.css(".card__dates").first
            date_text = (
                clean_text(dates_el.get_all_text(separator=" ", strip=True)) if dates_el else ""
            )
            start, end = parse_date_range(date_text)

            summary_el = card.css(".card__summary").first
            description = (
                clean_text(summary_el.get_all_text(separator=" ", strip=True)) if summary_el else ""
            )

            cat_el = card.css(".card__categories .category").first
            cat = cat_el.get_all_text(strip=True) if cat_el else ""

            image_url = _extract_image(card, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(f"{title} {description}", genre=cat),
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


def _extract_image(card: Selector, base_url: str) -> str | None:
    img = card.css(".card__image img").first
    if img is None:
        return None
    src = img.attrib.get("src") or img.attrib.get("data-src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    return urllib.parse.urljoin(base_url, src)
