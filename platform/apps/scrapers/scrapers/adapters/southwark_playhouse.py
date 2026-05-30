"""Southwark Playhouse — WP Grid Builder cards.

The site lists productions as `.wpgb-card` tiles. The generic
`a[href*="/productions/"]` selector grabbed each card's "Read More" / "Book Now"
footer links (and a `#book-tickets` duplicate) as separate junk-titled shows,
and missed the featured cards whose title isn't a link at all. We read each card
directly instead: title from `.wpgb-block-1`, canonical URL from the
`.wpgb-card-layer-link` overlay (present on every card), dates from
`.wpgb-block-3` ("8 May - 13 Jun 2026").
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
class SouthwarkPlayhouseAdapter(BaseAdapter):
    slug = "southwark-playhouse"
    url = "https://southwarkplayhouse.co.uk/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        out: list[Show] = []
        seen: set[str] = set()
        for card in page.css(".wpgb-card"):
            title_el = card.css(".wpgb-block-1").first
            link_el = card.css("a.wpgb-card-layer-link").first
            if title_el is None or link_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = link_el.attrib.get("href")
            if not title or not href:
                continue
            # The layer-link is the canonical production URL; drop any #fragment
            # so it dedupes against itself across a card's repeated links.
            url = urllib.parse.urljoin(base_url, str(href).split("#")[0])
            if "/productions/" not in url or url in seen:
                continue
            seen.add(url)

            date_el = card.css(".wpgb-block-3").first
            date_text = date_el.get_all_text(separator=" ", strip=True) if date_el else ""
            start, end = parse_date_range(date_text)

            img_el = card.css("img").first
            image = None
            if img_el is not None:
                image = img_el.attrib.get("src") or img_el.attrib.get("data-src")
            image_url = urllib.parse.urljoin(base_url, str(image)) if image else None

            try:
                out.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title, default="play"),
                        url=url,
                        start_date=start,
                        end_date=end,
                        image_url=image_url,
                    )
                )
            except Exception:
                continue
        return out
