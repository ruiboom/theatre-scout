"""Churchill Theatre, Bromley — JS-rendered Trafalgar Tickets venue page.
Generic adapter returned every "Just Added" badge text as a title because
the badge sits inside the same anchor that wraps the card. New adapter walks
each `<a href="/churchill-theatre-bromley/en-GB/event/<category>/<slug>">`
card and reads:

  <a title="<Title> Tickets" href="/churchill-theatre-bromley/.../event/<cat>/<slug>">
    <img alt="..." />
    <h2>Title</h2>
    <p>Eccentric villagers, shocking twists...</p>   ← short description
    <p>Tue 12 - Sat 16 May 2026</p>                  ← dates
  </a>
"""

from __future__ import annotations

import re
import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from ._html import parse_date_range
from .base import BaseAdapter
from .registry import register


@register
class ChurchillAdapter(BaseAdapter):
    slug = "churchill"
    url = "https://trafalgartickets.com/churchill-theatre-bromley/en-GB"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[href*="/event/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or "/event/" not in href:
                continue
            # Skip non-show paths e.g. /event-ticketing/, /event/, etc.
            if href.endswith("/event/") or "/event-ticketing/" in href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue
            # Featured cards use h2; carousel cards use h3. Take whichever appears.
            title_el = a.css("h2, h3").first
            if title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            if not title or title.lower() in {"just added", "on sale soon", "just announced"}:
                continue

            # Date can be in a <p> (featured cards) or <span> (carousel cards).
            description = ""
            date_text = ""
            for el in a.css("p, span"):
                txt = clean_text(el.get_all_text(separator=" ", strip=True))
                if not txt or txt == title:
                    continue
                if _looks_like_date(txt):
                    if not date_text:
                        date_text = txt
                elif not description and len(txt) > 20:
                    description = txt
                if description and date_text:
                    break
            start, end = parse_date_range(date_text)

            image_url = _extract_image(a, base_url)

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


_DATE_HINT_RE = re.compile(r"\d{1,2}\s+[A-Za-z]{3,}", re.IGNORECASE)


def _looks_like_date(text: str) -> bool:
    return bool(_DATE_HINT_RE.search(text))


def _extract_image(card: Selector, base_url: str) -> str | None:
    """Trafalgar wraps images in `_next/image?url=<encoded>`; unwrap to the
    underlying Contentful asset."""
    img = card.css("img").first
    if img is None:
        return None
    src = img.attrib.get("src") or img.attrib.get("data-src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    full = urllib.parse.urljoin(base_url, src)
    parsed = urllib.parse.urlparse(full)
    if parsed.path.endswith("/_next/image"):
        params = urllib.parse.parse_qs(parsed.query)
        wrapped = params.get("url", [None])[0]
        if wrapped:
            return urllib.parse.unquote(wrapped)
    return full
