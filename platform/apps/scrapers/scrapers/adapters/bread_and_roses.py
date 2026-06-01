"""Bread & Roses Theatre, Clapham — Weebly site whose /whats-on.html shows its
programme only via a LineupNow calendar widget.

`fetch()` does two hops. The LineupNow iframe URL is injected client-side by
calendar-loader.js, so it is *not* in the static HTML — but the publishable
apiKey is, in a stable `data-line-up-api-key` attribute. Hop 1 is therefore a
cheap non-stealth fetch of the Weebly page to read that key (no hard-coded
secret; survives rotation); we build the calendar URL and hop 2 stealth-renders
that React app. LineupNow's styled-component class names are build-hashed and
unstable, so `parse()` keys off the stable repeating text — `<title>` /
"The Bread & Roses Theatre" / "From:|Next Date: <date>". There are no per-show
links in the widget, so the listings page is canonical.

Mirrors scout/adapters/bread_and_roses.py.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter, _ClientLike
from .registry import register

_APIKEY_RE = re.compile(r'data-line-up-api-key="(pk_live_[A-Za-z0-9]+)"')
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
    # Hop 1 is plain HTTP (the apiKey lives in a static data attribute); only
    # the LineupNow render (hop 2) needs a browser. requires_js stays False so
    # enrich doesn't stealth-render the (shared) listings URL once per show.
    requires_js = False

    def fetch(self, client: _ClientLike) -> list[Show]:
        page_html = self._response_text(client.get(self.url, stealth=False))
        m = _APIKEY_RE.search(page_html)
        if m is None:
            # Page loaded fine but the publishable key is gone — a site-structure
            # change, not a fetch failure. Stays an empty (parse-level) result, so
            # the health monitor flags it as silent-zero rather than failed.
            return []
        cal_url = f"https://calendar.lineupnow.com?apiKey={m.group(1)}"
        cal_html = self._response_text(client.get(cal_url, stealth=True), url=cal_url)
        return self.parse(cal_html, cal_url)

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
