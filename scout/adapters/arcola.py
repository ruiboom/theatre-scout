"""Arcola Theatre — generic `a[href*="/event/"]` matched both "Find out more
for X" and "Book now for X" anchors per card. New adapter walks WordPress
`<article class="card card--event">` cards and reads:

  <h3 class="card__heading">Title</h3>
  <p class="type-body-l">By Author</p>           ← optional subtitle
  <span class="card__venue">Studio 2</span>      ← in .card__meta
  <span class="card__dates">6 May - 6 Jun 2026</span>
  <a class="card__fill-link" href="/event/<slug>/">Find out more</a>

Same template family as Lyric Hammersmith but the heading is a real `<h3>`
not a wrapper div, and there's no `.card__summary` here — the subtitle
is a plain `.type-body-l` paragraph between heading and meta.
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
class ArcolaAdapter(BaseAdapter):
    slug = "arcola"
    url = "https://www.arcolatheatre.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css("article.card--event"):
            heading = card.css(".card__heading").first
            link_el = card.css('a.card__fill-link, a[href*="/event/"]').first
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

            subtitle_el = card.css("p.type-body-l").first
            subtitle = (
                clean_text(subtitle_el.get_all_text(separator=" ", strip=True))
                if subtitle_el
                else ""
            )

            image_url = _extract_image(card, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(f"{title} {subtitle}"),
                        url=url,
                        description=subtitle,
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
    """Lazy-loaded with `data-src` (the `src` attribute is a base64 placeholder)."""
    img = card.css(".card__image img").first
    if img is None:
        return None
    src = img.attrib.get("data-src") or img.attrib.get("src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    return urllib.parse.urljoin(base_url, src)
