"""Regent's Park Open Air Theatre.

Listings live under `https://openairtheatre.com/whats-on/`. The page renders as
plain HTML (no JS needed) and groups productions inside per-year sections:

    <div class="Section">
      <h2 class="Section-title">At the Park</h2>
      <h3 class="Section-divide-title">2026</h3>
      <div class="ProductionTeaser-list--flex">
        <article class="ProductionTeaser ...">
          <a class="ProductionTeaser-link" href="...">
            <img class="ProductionTeaser-image" srcset="..." />
            <h1 class="ProductionTeaser-title">Sherlock Holmes</h1>
            <div class="ProductionTeaser-content">
              <span class="ProductionTeaser-content-dates">02 May – 06 June</span>
            </div>
          </a>
        </article>
        ...
      </div>
    </div>

Crucially, dates on the page omit the year — the surrounding `Section-divide-title`
h3 is the only year signal. We anchor parsing per-section so a future "2027"
header still works without changes. If a range straddles the new year
("20 December – 05 January"), the end month being before the start month bumps
the end year by one.

The generic adapter previously matched `<article>` but couldn't parse the title
or date reliably (the date string is whitespace-padded and there's no year in
the inline text), so every row landed with NULL `start_date`/`end_date`.
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

_MONTHS: dict[str, int] = {
    name: i + 1
    for i, name in enumerate(
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
_MONTH_LOOKUP: dict[str, int] = {**_MONTHS, **{k[:3]: v for k, v in _MONTHS.items()}}

# "02 May", "02 May 2026", "02 May – 06 June", "20 December – 05 January", etc.
# Dash is en-dash on the source page but allow ASCII hyphen too.
_DAY_MONTH = r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?"
_DATE_RE = re.compile(
    rf"{_DAY_MONTH}(?:\s*[–—\-]\s*{_DAY_MONTH})?",
)


def _parse_dates(text: str, year: int) -> tuple[date | None, date | None]:
    """Return (start, end). End is None for single-date entries.

    Dates on the page have no year — `year` comes from the surrounding section
    header. If the second month is calendar-before the first (e.g. Dec → Jan),
    bump the end year so the range stays chronological.
    """
    m = _DATE_RE.search(text)
    if not m:
        return None, None
    s_day, s_month_name, s_year, e_day, e_month_name, e_year = m.groups()
    s_month = _MONTH_LOOKUP.get(s_month_name) if s_month_name else None
    if s_month is None:
        return None, None
    try:
        start = date(int(s_year) if s_year else year, s_month, int(s_day))
    except ValueError:
        return None, None
    if e_day is None or e_month_name is None:
        return start, None
    e_month = _MONTH_LOOKUP.get(e_month_name)
    if e_month is None:
        return start, None
    end_year_int = int(e_year) if e_year else year
    # Bump year if the range crosses Jan 1 and the source omits the year.
    if e_year is None and e_month < s_month:
        end_year_int = year + 1
    try:
        end = date(end_year_int, e_month, int(e_day))
    except ValueError:
        return start, None
    return start, end


def _first_srcset_url(srcset: str) -> str | None:
    """Take the first URL out of a srcset string ("foo.jpg 1x, bar.jpg 2x")."""
    for chunk in srcset.split(","):
        url = chunk.strip().split(" ", 1)[0].strip()
        if url:
            return url
    return None


@register
class OpenAirTheatreAdapter(BaseAdapter):
    slug = "open-air-theatre"
    url = "https://openairtheatre.com/whats-on/"
    # Plain HTTP returns a fully populated DOM — no JS render needed.
    requires_js = False

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        shows: list[Show] = []
        seen: set[str] = set()

        # Walk year sections. Each section has an h3 with the year and a sibling
        # list of cards. Reading the year off the header is the only way to get
        # year context (cards don't carry it inline).
        for year_header in page.css("h3.Section-divide-title"):
            year_text = clean_text(year_header.get_all_text(strip=True))
            try:
                year = int(year_text)
            except ValueError:
                # Skip sections whose divider isn't a 4-digit year.
                continue

            section = year_header.parent
            if section is None:
                continue

            for card in section.css("article.ProductionTeaser"):
                title_el = card.css("h1.ProductionTeaser-title").first
                link_el = card.css("a.ProductionTeaser-link").first
                if title_el is None or link_el is None:
                    continue
                # `.text` is just the h1's direct text node — skips the
                # ProductionTeaser-subtitle child used for descriptions.
                title = clean_text(title_el.text or "")
                if not title:
                    continue

                href = str(link_el.attrib.get("href", "")).strip()
                if not href:
                    continue
                show_url = urllib.parse.urljoin(base_url, href)
                if show_url in seen:
                    continue

                date_el = card.css(".ProductionTeaser-content-dates").first
                start = end = None
                if date_el is not None:
                    date_text = date_el.get_all_text(separator=" ", strip=True)
                    start, end = _parse_dates(date_text, year)

                image_url: str | None = None
                img_el = card.css("img.ProductionTeaser-image").first
                if img_el is not None:
                    srcset = img_el.attrib.get("srcset")
                    src = img_el.attrib.get("src")
                    raw = src or (_first_srcset_url(srcset) if isinstance(srcset, str) else None)
                    if isinstance(raw, str) and raw and not raw.startswith("data:"):
                        image_url = urllib.parse.urljoin(base_url, raw)

                try:
                    shows.append(
                        Show(
                            theatre_slug=self.slug,
                            title=title,
                            show_type=classify(title),
                            url=show_url,
                            start_date=start,
                            end_date=end,
                            image_url=image_url,
                        )
                    )
                    seen.add(show_url)
                except Exception:
                    continue

        return shows
