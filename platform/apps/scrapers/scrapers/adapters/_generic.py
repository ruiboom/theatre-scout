"""Generic adapter components used by most per-theatre adapters.

Strategy:
  1. Try schema.org JSON-LD events. If found, return them.
  2. Otherwise iterate `card_selector` matches; pull title/link/dates per card.

Bespoke adapters override `parse()` directly when neither is enough.
Ported from scout/adapters/_generic.py.
"""

from __future__ import annotations

import logging
import re
import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show, ShowType
from ..text import clean_text
from ._html import parse_date_range
from ._jsonld import parse_jsonld
from .base import BaseAdapter

log = logging.getLogger(__name__)

_DATE_LIKE = re.compile(r"^[\d\s,.\-–:/]+$")
_GENERIC_BUTTON = re.compile(
    r"^(book|tickets|book tickets|find out more|read more|buy now|info|details)\b",
    re.IGNORECASE,
)
DESC_MAX_CHARS = 240


def _extract_description(card: Selector, title: str) -> str:
    """Pick the longest meaningful <p> in `card` that isn't the title or boilerplate."""
    best = ""
    for p in card.find_all("p"):
        text = clean_text(p.get_all_text(separator=" ", strip=True))
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
        cut = truncated.rsplit(" ", 1)[0]
        return cut + "…"
    return best


def _attrib_get(el: Selector, key: str) -> str | None:
    val = el.attrib.get(key)
    return str(val) if val else None


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
        page = Selector(html)
        seen_urls: set[str] = set()
        out: list[Show] = []
        for card in page.css(self.card_selector):
            show = self._card_to_show(card, base_url)
            if show is None:
                continue
            if show.url in seen_urls:
                continue
            seen_urls.add(show.url)
            out.append(show)
        return out

    def _card_to_show(self, card: Selector, base_url: str) -> Show | None:
        # When the selector itself is an anchor (e.g. a[href*="/whats-on/"]), treat
        # the link as the card; pull title from its text and look at the parent for dates.
        is_link_card = card.tag == "a" and "href" in card.attrib
        if is_link_card:
            link_el: Selector | None = card
            title = card.get_all_text(separator=" ", strip=True)
            text_source = card.parent if card.parent is not None else card
        else:
            title_el = card.css(self.title_selector).first
            link_el = card.css("a[href]").first
            if title_el is None or link_el is None:
                return None
            title = title_el.get_all_text(separator=" ", strip=True)
            text_source = card
        if not title or len(title) > 200 or link_el is None:
            return None
        href = _attrib_get(link_el, "href") or ""
        if not href or href.startswith(("#", "javascript:")):
            return None
        url = urllib.parse.urljoin(base_url, href)
        text = text_source.get_all_text(separator=" ", strip=True)
        start, end = parse_date_range(text)
        if self.require_date and start is None:
            return None
        img_el = (
            (card.parent.css("img").first if card.parent is not None else None)
            if is_link_card
            else card.css("img").first
        )
        image = None
        if img_el is not None:
            image = _attrib_get(img_el, "src") or _attrib_get(img_el, "data-src")
        image_url = urllib.parse.urljoin(base_url, image) if image else None
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
