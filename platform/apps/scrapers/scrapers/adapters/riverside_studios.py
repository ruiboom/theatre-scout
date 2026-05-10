"""Riverside Studios — JS-rendered listing. Plain HTTP returned 0 events
because <main> is just "Loading results...". After stealth render each event
is a `<div class="slot event">` containing:

  <h3 class="slot-title">Title</h3>
  <div class="slot-date">Sat 25 Apr - Sat 20 Jun 2026</div>
  <div class="event-tag">Wellness</div>             ← genre pill
  <a class="button" href="https://.../whats-on/<slug>/">More Info</a>
  <img srcset="..." />
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

# srcset is a comma-separated list of "URL widthSpec" pairs; we want the URL
# from the first pair as a fallback when img.src is itself unset.
_SRCSET_FIRST_RE = re.compile(r"^\s*([^\s,]+)")


@register
class RiversideStudiosAdapter(BaseAdapter):
    slug = "riverside-studios"
    url = "https://riversidestudios.co.uk/whats-on/"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".slot.event"):
            title_el = card.css(".slot-title").first
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

            date_el = card.css(".slot-date").first
            date_text = (
                clean_text(date_el.get_all_text(separator=" ", strip=True)) if date_el else ""
            )
            start, end = parse_date_range(date_text)

            tag_el = card.css(".event-tag").first
            tag = tag_el.get_all_text(strip=True) if tag_el else ""

            image_url = _extract_image(card, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(f"{title} {tag}"),
                        url=url,
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
    img = card.css("img").first
    if img is None:
        return None
    src = img.attrib.get("src")
    if isinstance(src, str) and src and not src.startswith("data:"):
        return str(urllib.parse.urljoin(base_url, src))
    srcset = img.attrib.get("srcset")
    if isinstance(srcset, str) and srcset:
        m = _SRCSET_FIRST_RE.match(srcset)
        if m:
            return str(urllib.parse.urljoin(base_url, m.group(1)))
    return None
