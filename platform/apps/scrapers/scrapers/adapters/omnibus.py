"""Omnibus Theatre, Clapham — JS-rendered Wix site. The homepage just shows a
"Click to find event" dropdown so we point at `/whatson` instead, where the
visible event repeater lists each show as `<div role="listitem">` with a
`MORE INFO` button linking to `/whatson/<slug>`.

Wix's CSS classes are auto-generated hashes so we anchor on the only stable
hooks: `role="listitem"` for the card and `aria-label="MORE INFO"` for the
canonical URL anchor. Everything else (title, dates, image) is fished out
relative to those.
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

# Strict month-abbreviation match — "96 FESTIVAL" looked date-shaped to the
# loose regex and then "96 FESTIVAL 2026" came back as a date string.
_DATE_HINT_RE = re.compile(
    r"\b\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\b",
    re.IGNORECASE,
)

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    )
}
_MONTHS["SEPT"] = 9  # Wix sometimes writes the 4-letter form

# `25 MAY | 28 SEPT` or `4 JUN - 12 JUL` or just `25 MAY`. Assumes current year
# since Omnibus drops the year from the listing meta.
_DAY_MONTH_RE = re.compile(
    r"\b(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\b",
    re.IGNORECASE,
)


@register
class OmnibusAdapter(BaseAdapter):
    slug = "omnibus"
    url = "https://www.omnibus-clapham.org/whatson"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css('[role="listitem"]'):
            link_el = card.css('a[aria-label="MORE INFO"][href*="/whatson/"]').first
            if link_el is None:
                # Some sections use other repeaters (newsletter, sponsors, etc.);
                # those won't have a /whatson/ MORE INFO anchor, so skip silently.
                continue
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or href.rstrip("/").endswith("/whatson"):
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            title, date_text = _extract_title_and_date(card)
            if not title:
                continue
            start, end = _parse_day_month(date_text)

            image_url = _extract_image(card, base_url)

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
                seen.add(url)
            except Exception:
                continue
        return shows


def _extract_title_and_date(card: Selector) -> tuple[str, str]:
    """Headings inside a Wix card carry a mix of title text and date text in
    separate `<h2>` elements. Heuristic: first heading whose text doesn't look
    like a date is the title, first heading that does look like a date is the
    date string."""
    title = ""
    date_text = ""
    for h in card.css("h1, h2, h3"):
        txt = clean_text(h.get_all_text(separator=" ", strip=True))
        if not txt:
            continue
        if _DATE_HINT_RE.search(txt) and not date_text:
            date_text = txt
        elif not title:
            title = txt
        if title and date_text:
            break
    return title, date_text


def _parse_day_month(text: str) -> tuple[date | None, date | None]:
    """Parse "25 MAY | 28 SEPT" or "4 JUN - 12 JUL" or "25 MAY".

    Year is missing from Wix listings — assume current year, and roll the year
    forward if start would be in the past relative to today (covers the Dec→Jan
    boundary case).
    """
    matches = _DAY_MONTH_RE.findall(text)
    if not matches:
        return None, None
    today = date.today()
    year = today.year
    parsed: list[date] = []
    for d, m in matches:
        month = _MONTHS.get(m.upper())
        if month is None:
            continue
        try:
            d_obj = date(year, month, int(d))
        except ValueError:
            continue
        # Roll the year forward if a candidate date is more than ~3 months in
        # the past — implies it really meant next year.
        if (today - d_obj).days > 90:
            try:
                d_obj = date(year + 1, month, int(d))
            except ValueError:
                continue
        parsed.append(d_obj)
    if not parsed:
        return None, None
    if len(parsed) == 1:
        return parsed[0], parsed[0]
    return parsed[0], parsed[-1]


def _extract_image(card: Selector, base_url: str) -> str | None:
    img = card.css("img").first
    if img is None:
        return None
    src = img.attrib.get("src") or img.attrib.get("data-src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    return urllib.parse.urljoin(base_url, src)
