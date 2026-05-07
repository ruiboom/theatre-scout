"""Park Theatre — bespoke because the listing renders 3 links per show
(heading link, "Book now" link with `#event-instances` fragment, and an image link).

Strategy:
  1. Group all links into /events/ by canonical URL (strip `#event-instances`).
  2. For each group, pick the cleanest title we can derive.
"""

from __future__ import annotations

import re
import urllib.parse

from bs4 import BeautifulSoup, Tag

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show

_FIND_OUT_MORE_RE = re.compile(r"^find out more about[\s:]*", re.IGNORECASE)
_BOOK_NOW_PREFIX = re.compile(r"^book now[\s:]*", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


@register
class ParkTheatreAdapter(BaseAdapter):
    slug = "park-theatre"
    url = "https://parktheatre.co.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        soup = BeautifulSoup(html, "lxml")
        groups: dict[str, list[Tag]] = {}
        for a in soup.select('a[href*="/events/"]'):
            href = str(a.get("href", "")).split("#", 1)[0]
            if not href or href.endswith("/events/"):
                continue
            canonical = urllib.parse.urljoin(base_url, href)
            groups.setdefault(canonical, []).append(a)

        shows: list[Show] = []
        for url, links in groups.items():
            title = self._best_title(links)
            if not title:
                continue
            text_blob = " ".join(a.get_text(" ", strip=True) for a in links)
            start, end = parse_date_range(text_blob)
            image_url = self._find_image(links, base_url)
            description = ""  # populated by --enrich on the detail page
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=url,
                        description=description,
                        start_date=start,
                        end_date=end,
                        image_url=image_url,
                    )
                )
            except Exception:
                continue
        return shows

    @staticmethod
    def _best_title(links: list[Tag]) -> str:
        # Heading inside the link is canonical
        for a in links:
            heading = a.find(["h1", "h2", "h3", "h4"])
            if heading:
                return _clean(heading.get_text(" ", strip=True))
        # aria-label like "Book now: Show Title"
        for a in links:
            aria = a.get("aria-label")
            if isinstance(aria, str):
                stripped = _BOOK_NOW_PREFIX.sub("", aria).strip()
                if stripped and stripped.lower() != "book now":
                    return _clean(stripped)
        # Strip "Find out more about" prefix from link text
        for a in links:
            text = a.get_text(" ", strip=True)
            cleaned = _FIND_OUT_MORE_RE.sub("", text).strip()
            if cleaned and cleaned.lower() not in {"book now", ""}:
                return _clean(cleaned)
        return ""

    @staticmethod
    def _find_image(links: list[Tag], base_url: str) -> str | None:
        for a in links:
            img = a.find("img")
            if isinstance(img, Tag):
                src = img.get("src") or img.get("data-src")
                if isinstance(src, str) and src:
                    return urllib.parse.urljoin(base_url, src)
        return None


def _clean(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()
