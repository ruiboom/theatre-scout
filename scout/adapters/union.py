"""Union Theatre — bespoke listing parser and bespoke detail-page enricher.

Listing page: anchors say "Read more" so the generic adapter picks up button
text. We walk `.thumbnail` cards and read `.caption h2` for titles and
`.caption .dates` for date ranges.

Detail page: Wordpress site with no `<main>`/`<article>` wrapper, so the generic
description extractor returns nothing. Synopsis paragraphs (when present) live
as plain `<p>` inside `#show`. The page also exposes structured ticket prices
in the form `<h2>Tickets</h2><ul><li>...<strong>£13</strong></li>...</ul>` —
we map those to `price_min` / `price_max` in pence, skipping £0 (access/comp).
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text, is_boilerplate

_PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{1,2})?)")
_DESC_MAX_CHARS = 600
_DESC_MIN_CHARS = 60


@register
class UnionAdapter(BaseAdapter):
    slug = "union"
    url = "https://uniontheatre.biz/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen_urls: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".thumbnail"):
            link_el = card.css('a[href*="/show/"]').first
            title_el = card.css(".caption h2").first
            if link_el is None or title_el is None:
                continue
            title = title_el.get_all_text(separator=" ", strip=True)
            if not title:
                continue
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen_urls:
                continue

            dates_el = card.css(".caption .dates").first
            date_text = dates_el.get_all_text(separator=" ", strip=True) if dates_el else ""
            start, end = parse_date_range(date_text)

            img_el = card.css("img.img-responsive").first
            image_url: str | None = None
            if img_el is not None:
                src = img_el.attrib.get("src") or img_el.attrib.get("data-src")
                if isinstance(src, str) and src:
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
                seen_urls.add(url)
            except Exception:
                continue
        return shows

    def enrich(self, html: str, base_url: str) -> dict[str, Any]:
        page = Selector(html)
        out: dict[str, Any] = {}
        desc = _extract_description(page)
        if desc:
            out["description"] = desc
        lo, hi = _extract_prices(page)
        if lo is not None:
            out["price_min"] = lo
        if hi is not None:
            out["price_max"] = hi
        return out


def _extract_description(page: Selector) -> str:
    """First substantive `<p>` inside `#show`. Mirrors the generic extractor's
    "first qualifying paragraph wins" rule."""
    show = page.css("#show").first
    if show is None:
        return ""
    for p in show.css("p"):
        text = clean_text(p.get_all_text(separator=" ", strip=True))
        if len(text) < _DESC_MIN_CHARS or is_boilerplate(text):
            continue
        if len(text) > _DESC_MAX_CHARS:
            return text[:_DESC_MAX_CHARS].rsplit(" ", 1)[0] + "…"
        return text
    return ""


def _extract_prices(page: Selector) -> tuple[int | None, int | None]:
    """Find the Tickets `<h2>` heading and pull every `£N` from the next `<ul>`.

    Skips £0 entries — the Union uses those for access seats and comps, which
    aren't representative of the show's actual price.
    """
    for h2 in page.css("h2"):
        if h2.get_all_text(strip=True).lower() != "tickets":
            continue
        sib = h2.next
        if sib is None or sib.tag != "ul":
            continue
        prices: list[int] = []
        for strong in sib.css("strong"):
            m = _PRICE_RE.search(strong.get_all_text(strip=True))
            if not m:
                continue
            pence = int(round(float(m.group(1)) * 100))
            if pence > 0:
                prices.append(pence)
        if prices:
            return min(prices), max(prices)
        return None, None
    return None, None
