"""Bread & Roses Theatre, Clapham — Weebly site whose /whats-on.html embeds a
LineupNow calendar in an iframe; the real programme is only in that widget.

`fetch()` does two hops: load the Weebly page, pull the LineupNow calendar URL
out of the iframe (so we never hard-code their publishable apiKey and survive
key rotation), then render that React app. LineupNow's styled-component class
names are build-hashed and unstable, so `parse()` keys off the stable repeating
text — `<title>` / "The Bread & Roses Theatre" / "From:|Next Date: <date>".
There are no per-show links in the widget, so the listings page is canonical.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter, _ClientLike
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

_LINEUPNOW_RE = re.compile(r"https://calendar\.lineupnow\.com/?\?apiKey=[A-Za-z0-9_]+")
_VENUE = "the bread & roses theatre"
_DATE_RE = re.compile(r"(?:From|Next Date):\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})")


def _parse_date(text: str) -> date | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    raw = m.group(1)
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


@register
class BreadAndRosesAdapter(BaseAdapter):
    slug = "bread-and-roses"
    url = "https://www.breadandrosestheatre.co.uk/whats-on.html"
    requires_js = True

    def fetch(self, client: _ClientLike) -> list[Show]:
        resp = client.get(self.url, stealth=self.requires_js)
        if resp is None:
            return []
        page_html = getattr(resp, "text", "") or getattr(resp, "content", b"").decode(
            "utf-8", errors="replace"
        )
        m = _LINEUPNOW_RE.search(page_html)
        if m is None:
            return []
        cal = client.get(m.group(0), stealth=True)
        if cal is None:
            return []
        cal_html = getattr(cal, "text", "") or getattr(cal, "content", b"").decode(
            "utf-8", errors="replace"
        )
        return self.parse(cal_html, m.group(0))

    def parse(self, html: str, base_url: str) -> list[Show]:
        lines = [
            ln.strip()
            for ln in Selector(html).get_all_text(separator="\n").split("\n")
            if ln.strip()
        ]
        seen: set[str] = set()
        shows: list[Show] = []
        for i, line in enumerate(lines):
            if line.lower() != _VENUE:
                continue
            title = clean_text(lines[i - 1]) if i else ""
            key = title.lower()
            if not title or len(title) > 200 or key in seen or key == _VENUE:
                continue
            start = _parse_date(" ".join(lines[i + 1 : i + 3]))
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=self.url,
                        start_date=start,
                    )
                )
                seen.add(key)
            except Exception:
                continue
        return shows
