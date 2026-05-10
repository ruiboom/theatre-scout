"""Shared parser for Troubadour Theatres venue pages.

Each venue lives at `https://www.troubadourtheatres.com/<venue>-theatre`. The
old generic adapter pointed at `https://troubadour.com/<venue>` (the LA
Troubadour's site, unrelated) and got 404s. Each show on the venue page is a
`<div class="c-featured-event">` with:

  <a href="https://www.troubadourtheatres.com/whats-on/<slug>">
    <div role="img" style="background-image: url(<image-url>)">
  </a>
  <div class="c-featured-event__details">
    <div class="c-featured-event__details__meta">From 22 July 2026</div>
    <h3 class="c-featured-event__details__title">Title</h3>
    <div class="c-featured-event__details__discription">LIMITED SEASON 22 JUL - 27 SEP</div>
  </div>
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

_BG_IMG_RE = re.compile(r"url\(([^)]+)\)")


def parse_troubadour(html: str, base_url: str, *, theatre_slug: str) -> list[Show]:
    page = Selector(html)
    seen: set[str] = set()
    shows: list[Show] = []
    for card in page.css(".c-featured-event"):
        title_el = card.css(".c-featured-event__details__title").first
        link_el = card.css('a[href*="/whats-on/"]').first
        if title_el is None or link_el is None:
            continue
        title = clean_text(title_el.get_all_text(separator=" ", strip=True))
        href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
        if not title or not href or href.endswith("/whats-on/"):
            continue
        url = urllib.parse.urljoin(base_url, href)
        if url in seen:
            continue

        start, end = _extract_dates(card)
        image_url = _extract_bg_image(card, base_url)
        description = _extract_description(card)

        try:
            shows.append(
                Show(
                    theatre_slug=theatre_slug,
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


def _extract_dates(card: Selector) -> tuple[date | None, date | None]:
    """Try the meta line first ("From 22 July 2026") then the description
    ("LIMITED SEASON 22 JUL - 27 SEP")."""
    for sel in [".c-featured-event__details__meta", ".c-featured-event__details__discription"]:
        el = card.css(sel).first
        if el is None:
            continue
        text = clean_text(el.get_all_text(separator=" ", strip=True))
        start, end = parse_date_range(text)
        if start is not None or end is not None:
            return start, end
    return None, None


def _extract_bg_image(card: Selector, base_url: str) -> str | None:
    """Background image is set inline on a `<div role="img" style="background-image:url(...)">`."""
    for el in card.css('[style*="background-image"]'):
        style = str(el.attrib.get("style", ""))
        m = _BG_IMG_RE.search(style)
        if m:
            url = m.group(1).strip().strip("'\"")
            return str(urllib.parse.urljoin(base_url, url))
    return None


def _extract_description(card: Selector) -> str:
    el = card.css(".c-featured-event__details__discription").first
    if el is None:
        return ""
    return clean_text(el.get_all_text(separator=" ", strip=True))
