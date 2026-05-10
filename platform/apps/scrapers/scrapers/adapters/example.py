"""Example bespoke adapter.

Copy this file when adding a new venue whose listings page resists the
GenericAdapter pattern (button-text titles, custom date format, JS-rendered,
etc). Set `slug`, `url`, optionally `requires_js`, and implement `parse()`.

The orchestrator handles the HTTP fetch — your `parse()` is a pure function of
(html, base_url) -> list[Show] so it's trivially testable from a fixture.

Mirrors scout/adapters/almeida.py / pleasance.py / soho_theatre.py shape.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from ._html import parse_date_range
from .base import BaseAdapter
from .registry import register


@register
class ExampleAdapter(BaseAdapter):
    slug = "example"
    url = "https://example.com/whats-on"
    requires_js = False  # set True for SPA / anti-bot venues

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        out: list[Show] = []
        for card in page.css(".show-card"):
            link = card.css("a[href]").first
            title_el = card.css("h2, h3").first
            if link is None or title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = link.attrib.get("href") or ""
            if not title or not href:
                continue
            text = card.get_all_text(separator=" ", strip=True)
            start, end = parse_date_range(text)
            try:
                show = Show(
                    theatre_slug=self.slug,
                    title=title,
                    show_type=classify(title),
                    url=urllib.parse.urljoin(base_url, str(href)),
                    start_date=start,
                    end_date=end,
                )
            except Exception:
                continue
            out.append(show)
        return out
