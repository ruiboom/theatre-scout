"""Tramshed, Woolwich — comedy & music venue on a Wix site (JS-rendered, so
requires_js). On /whatson each production is a section whose heading carries
the show title; bookings go through a single Ticket Tailor store (no per-show
URL), so the listings page is the canonical link. Comedy-leaning programme, so
that is the classification fallback.

Mirrors scout/adapters/tramshed.py.
"""

from __future__ import annotations

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter
from .registry import register

# Headings that are page furniture, not shows.
_SKIP = {
    "what's on",
    "what’s on",
    "whats on",
    "tramshed",
    "home",
    "about",
    "about us",
    "contact",
    "contact us",
    "get in touch",
    "book now",
    "tickets",
    "newsletter",
    "sign up",
    "find us",
    "opening hours",
    "our programme",
    "support us",
    "hire",
}


@register
class TramshedAdapter(BaseAdapter):
    slug = "tramshed"
    url = "https://www.tramshed.org/whatson"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for h in page.css("h1, h2, h3, h4"):
            title = clean_text(h.get_all_text(separator=" ", strip=True))
            key = title.lower()
            if not title or len(title) < 3 or len(title) > 120:
                continue
            if key in _SKIP or key in seen:
                continue
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title, default="comedy"),
                        url=self.url,
                    )
                )
                seen.add(key)
            except Exception:
                continue
        return shows
