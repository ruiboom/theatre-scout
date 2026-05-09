"""The Vaults — listing redirects to a single-event Lineup pages.dev page.

The Vaults run as a venue-for-hire / occasional-events space; their
`thevaults.london/whats-on` page bounces straight to a Lineup-rendered event
detail at `line-up-the-vaults.pages.dev/event/<id>/info`. So this adapter
parses that single-event page directly:

  - Title from <h1>
  - Description from the synopsis paragraphs
  - Image from the imgix poster
  - Date range from the calendar component (react-day-picker), reading
    `aria-label="<weekday> <month> <day> <year>"` on every non-disabled day
    cell that has a time span (e.g. "7:30pm").

Falls back gracefully if the redirect ever lands on a true listing page —
returns [] so the run is a no-op rather than crashing.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text, is_boilerplate

_TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b", re.IGNORECASE)
_ARIA_DATE_RE = re.compile(r"^\w+\s+(\w+)\s+(\d{1,2})\s+(\d{4})$")
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    )
}
_MONTHS.update({k[:3]: v for k, v in dict(_MONTHS).items()})


@register
class VaultsAdapter(BaseAdapter):
    slug = "vaults"
    url = "https://line-up-the-vaults.pages.dev/"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        title_el = page.css("h1").first
        if title_el is None:
            return []
        title = title_el.get_all_text(separator=" ", strip=True)
        if not title:
            return []

        # Resolve the canonical event URL: prefer the first /event/<id> link on
        # the page (the "Book now" button), fall back to the page URL.
        url = base_url
        for a in page.css('a[href*="/event/"]'):
            href = str(a.attrib.get("href", ""))
            if re.search(r"/event/\d+", href):
                url = urllib.parse.urljoin(base_url, href.split("?", 1)[0])
                break

        start, end = _extract_calendar_dates(page)
        image_url = _extract_image(page, base_url)
        description = _extract_description(page, title)

        try:
            return [
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
            ]
        except Exception:
            return []


def _extract_calendar_dates(page: Selector) -> tuple[date | None, date | None]:
    """Walk react-day-picker cells; collect dates for non-disabled days that
    contain a time string. Returns (min, max) or (None, None)."""
    dates: list[date] = []
    for cell in page.css(".rdp-day"):
        cls = str(cell.attrib.get("class", ""))
        if "rdp-day_disabled" in cls:
            continue
        cell_text = cell.get_all_text(separator=" ", strip=True)
        if not _TIME_RE.search(cell_text):
            continue
        aria_span = cell.css("span[aria-label]").first
        if aria_span is None:
            continue
        m = _ARIA_DATE_RE.match(str(aria_span.attrib.get("aria-label", "")).strip())
        if not m:
            continue
        month_name, day_str, year_str = m.groups()
        month = _MONTHS.get(month_name)
        if month is None:
            continue
        try:
            dates.append(date(int(year_str), month, int(day_str)))
        except ValueError:
            continue
    if not dates:
        return None, None
    return min(dates), max(dates)


def _extract_image(page: Selector, base_url: str) -> str | None:
    """Prefer real image hosts (e.g. imgix) over inline base64 placeholders."""
    for img in page.css("img"):
        src = img.attrib.get("src") or img.attrib.get("data-src")
        if not isinstance(src, str) or not src or src.startswith("data:"):
            continue
        return urllib.parse.urljoin(base_url, src)
    return None


def _extract_description(page: Selector, title: str) -> str:
    """First substantive paragraph that isn't the venue address or boilerplate."""
    for p in page.css("p"):
        text = clean_text(p.get_all_text(separator=" ", strip=True))
        if len(text) < 60 or is_boilerplate(text):
            continue
        if text.lower() == title.lower():
            continue
        if len(text) > 600:
            return text[:600].rsplit(" ", 1)[0] + "…"
        return text
    return ""
