"""Donmar Warehouse — bespoke because every card has 'Book now' and 'More info'
buttons that the generic `a[href*="/events/"]` selector would pick up as titles.

The page is plain HTML with semantic markup: each show is a `.c-media--event`
card containing `<h3 class="c-media__title">`, ISO-stamped `<time>` elements
with `itemprop="startDate"`/`endDate`, a `.c-media__summary` paragraph and
multiple responsive `<img>` variants.
"""

from __future__ import annotations

import urllib.parse
from datetime import date, datetime

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text


@register
class DonmarWarehouseAdapter(BaseAdapter):
    slug = "donmar-warehouse"
    url = "https://www.donmarwarehouse.com/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".c-media--event"):
            title_el = card.css(".c-media__title").first
            if title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            if not title:
                continue

            # Both "Book now" (#content-dates-and-times) and "More info" point at
            # the same /events/<slug>; either survives the fragment strip.
            link_el = card.css('a[href*="/events/"]').first
            if link_el is None:
                continue
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            start, end = _extract_iso_dates(card)
            description = _extract_summary(card)
            image_url = _extract_image(card, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(f"{title} {description}"),
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


def _extract_iso_dates(card: Selector) -> tuple[date | None, date | None]:
    """Read `<time itemprop="startDate"|"endDate" datetime="ISO8601">` pairs."""

    def _parse(prop: str) -> date | None:
        el = card.css(f'time[itemprop="{prop}"]').first
        if el is None:
            return None
        raw = str(el.attrib.get("datetime", "")).strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            return None

    start = _parse("startDate")
    end = _parse("endDate")
    # Single-date shows omit the endDate <time>; mirror start to end so the UI
    # can render a definite date instead of "open-ended".
    if start is not None and end is None:
        end = start
    return start, end


def _extract_summary(card: Selector) -> str:
    summary = card.css(".c-media__summary").first
    if summary is None:
        return ""
    return clean_text(summary.get_all_text(separator=" ", strip=True))


def _extract_image(card: Selector, base_url: str) -> str | None:
    """Donmar serves four responsive variants per card (`-s`/`-m`/`-l`/`-h`).
    Prefer the large desktop variant; fall back to whatever's first."""
    for sel in [".c-media__image-l img", ".c-media__image-m img", "img.o-image__img"]:
        img = card.css(sel).first
        if img is None:
            continue
        src = img.attrib.get("src") or img.attrib.get("data-src")
        if isinstance(src, str) and src and not src.startswith("data:"):
            return urllib.parse.urljoin(base_url, src)
    return None
