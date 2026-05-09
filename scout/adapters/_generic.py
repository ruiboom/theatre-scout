"""Generic adapter components used by most per-theatre adapters.

Strategy:
  1. Try schema.org JSON-LD events. If found, return them.
  2. Otherwise iterate `card_selector` matches; pull title/link/dates per card.

Bespoke adapters override `parse()` directly when neither is enough.
"""

from __future__ import annotations

import logging
import re
import urllib.parse

from bs4 import BeautifulSoup, Tag

from scout.adapters._html import parse_date_range
from scout.adapters._jsonld import parse_jsonld
from scout.adapters.base import BaseAdapter
from scout.classify import classify
from scout.models import Show, ShowType
from scout.text import clean_text

log = logging.getLogger(__name__)

_DATE_LIKE = re.compile(r"^[\d\s,.\-–:/]+$")
_GENERIC_BUTTON = re.compile(
    r"^(book|tickets|book tickets|find out more|read more|buy now|info|details)\b",
    re.IGNORECASE,
)
DESC_MAX_CHARS = 240


def _extract_description(card: Tag, title: str) -> str:
    """Pick the longest meaningful <p> in `card` that isn't the title or boilerplate."""
    best = ""
    for p in card.find_all("p"):
        text = clean_text(p.get_text(" ", strip=True))
        if not text or text == title or len(text) < 20:
            continue
        if _DATE_LIKE.match(text) or _GENERIC_BUTTON.match(text):
            continue
        if len(text) > len(best):
            best = text
    if not best:
        return ""
    if len(best) > DESC_MAX_CHARS:
        truncated = best[:DESC_MAX_CHARS]
        # don't break mid-word
        cut = truncated.rsplit(" ", 1)[0]
        return cut + "…"
    return best


class GenericAdapter(BaseAdapter):
    """Default adapter: JSON-LD first, then HTML cards."""

    card_selector: str = ""
    title_selector: str = "h1, h2, h3"
    default_show_type: ShowType = "play"
    require_date: bool = False  # filter out cards with no parseable date

    def parse(self, html: str, base_url: str) -> list[Show]:
        shows = parse_jsonld(html, theatre_slug=self.slug, base_url=base_url)
        if shows:
            return shows
        if not self.card_selector:
            return []
        return self._parse_cards(html, base_url)

    def _parse_cards(self, html: str, base_url: str) -> list[Show]:
        soup = BeautifulSoup(html, "lxml")
        seen_urls: set[str] = set()
        out: list[Show] = []
        for card in soup.select(self.card_selector):
            show = self._card_to_show(card, base_url)
            if show is None:
                continue
            if show.url in seen_urls:
                continue
            seen_urls.add(show.url)
            out.append(show)
        return out

    def _card_to_show(self, card: Tag, base_url: str) -> Show | None:
        # When the selector itself is an anchor (e.g. a[href*="/whats-on/"]), treat
        # the link as the card; pull title from its text and look at the parent for dates.
        if card.name == "a" and card.has_attr("href"):
            link_el: Tag | None = card
            title = card.get_text(" ", strip=True)
            text_source: Tag = card.parent or card
        else:
            title_el = card.select_one(self.title_selector)
            link_el = card.find("a", href=True) if isinstance(card, Tag) else None
            if not title_el or not link_el:
                return None
            title = title_el.get_text(" ", strip=True)
            text_source = card
        if not title or len(title) > 200 or link_el is None:
            return None
        href = str(link_el["href"])
        if href.startswith("#") or href.startswith("javascript:"):
            return None
        url = urllib.parse.urljoin(base_url, href)
        text = text_source.get_text(" ", strip=True)
        start, end = parse_date_range(text)
        if self.require_date and start is None:
            return None
        img_el = (
            card.find("img")
            if card.name != "a"
            else (card.parent.find("img") if card.parent else None)
        )
        image = (img_el.get("src") or img_el.get("data-src")) if isinstance(img_el, Tag) else None
        image_url = urllib.parse.urljoin(base_url, str(image)) if image else None
        description = _extract_description(text_source, title)
        show_type = classify(f"{title} {description}", default=self.default_show_type)
        try:
            return Show(
                theatre_slug=self.slug,
                title=title,
                show_type=show_type,
                url=url,
                description=description,
                start_date=start,
                end_date=end,
                image_url=image_url,
            )
        except Exception:
            return None
