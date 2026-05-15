"""Bloomsbury Theatre — JS-rendered listing at /events with everything inline.

The old `/whats-on/` URL 404s; the working listing lives at `/events` and is
behind a SPA. After stealth render every show is a `<li class="es-card">` with
title, image, date(s), description and a category pill all inside the card —
no enrichment fetch needed. UCL's venue runs talks / comedy / film / charity
nights as well as theatre, so most rows classify to `other` or `comedy`.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter
from .registry import register

_UK_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


@register
class BloomsburyAdapter(BaseAdapter):
    slug = "bloomsbury"
    url = "https://www.bloomsburytheatre.com/events"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".es-card"):
            link_el = card.css("a.es-card-link").first
            title_el = card.css(".es-title").first
            if link_el is None or title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", ""))
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href.split("?", 1)[0])
            if url in seen:
                continue

            meta_el = card.css(".es-meta").first
            meta_text = meta_el.get_all_text(separator=" ", strip=True) if meta_el else ""
            start, end = _parse_uk_dates(meta_text)

            desc_el = card.css(".es-desc").first
            description = (
                clean_text(desc_el.get_all_text(separator=" ", strip=True)) if desc_el else ""
            )

            img_el = card.css("img.es-card-img").first
            image_url: str | None = None
            if img_el is not None:
                src = img_el.attrib.get("src") or img_el.attrib.get("data-src")
                if isinstance(src, str) and src and not src.startswith("data:"):
                    image_url = urllib.parse.urljoin(base_url, src)

            tag_el = card.css(".es-pill").first
            tag = tag_el.get_all_text(strip=True) if tag_el else ""
            show_type = classify(f"{title} {description}", genre=tag, default="other")

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=show_type,
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


def _parse_uk_dates(text: str) -> tuple[date | None, date | None]:
    """Parse `dd/mm/yyyy [HH:MM]` or `dd/mm/yyyy - dd/mm/yyyy`. Returns (start, end)."""
    matches = _UK_DATE_RE.findall(text)
    dates: list[date] = []
    for d, m, y in matches:
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    if not dates:
        return None, None
    if len(dates) == 1:
        return dates[0], dates[0]
    return dates[0], dates[-1]
