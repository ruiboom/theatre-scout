"""Etcetera Theatre — Squarespace `eventlist` page. Generic adapter found 0
shows because every event card has multiple `/events/<slug>` anchors plus an
`?format=ical` export link, which the heuristic conflated.

Each event is an `<article class="eventlist-event">` with:

  <h1 class="eventlist-title"><a href="/events/<slug>">Title</a></h1>
  <time class="event-date" datetime="2026-05-10">Sunday 10 May 2026</time>
  <div class="eventlist-excerpt">Description...</div>
  <img src="..." />
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
class EtceteraAdapter(BaseAdapter):
    slug = "etcetera"
    url = "https://www.etceteratheatrecamden.com/events/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css("article.eventlist-event"):
            link_el = card.css("h1.eventlist-title a, .eventlist-title-link").first
            if link_el is None:
                continue
            title = clean_text(link_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            start, end = _extract_iso_dates(card)
            description = _extract_excerpt(card)
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
    """Squarespace renders `<time class="event-date" datetime="YYYY-MM-DD">`."""
    el = card.css("time.event-date").first
    if el is None:
        return None, None
    raw = str(el.attrib.get("datetime", "")).strip()
    if not raw:
        return None, None
    try:
        d = datetime.fromisoformat(raw).date()
    except ValueError:
        return None, None
    return d, d


def _extract_excerpt(card: Selector) -> str:
    el = card.css(".eventlist-excerpt").first
    if el is None:
        return ""
    return clean_text(el.get_all_text(separator=" ", strip=True))


def _extract_image(card: Selector, base_url: str) -> str | None:
    img = card.css("img").first
    if img is None:
        return None
    src = img.attrib.get("data-image") or img.attrib.get("data-src") or img.attrib.get("src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    return urllib.parse.urljoin(base_url, src)
