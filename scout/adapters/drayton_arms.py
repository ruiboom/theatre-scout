"""Drayton Arms — JS-rendered Cube Portfolio gallery. Plain-HTTP returned 0
event hrefs because the cards aren't anchored as event links per se. After
stealth render each show is a `<div class="cbp-item">` with:

  <img alt="Title" src="..." />
  <ul>
    <li><a href="tickets/<slug>"><i class="fa fa-ticket"></i></a></li>
    <li><a href="/<slug>"><i class="fa fa-info"></i></a></li>     ← canonical URL
  </ul>
  <h3>Title</h3>
  <p>10th May 2026 - 11th May 2026</p>
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
from scout.text import clean_text

_MONTHS = {
    name.lower(): i + 1
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
_MONTHS.update({k[:3]: v for k, v in dict(_MONTHS).items()})

# `10th May 2026` — number-with-ordinal-suffix + month + year.
_UK_ORDINAL_DATE_RE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", re.IGNORECASE
)


@register
class DraytonArmsAdapter(BaseAdapter):
    slug = "drayton-arms"
    url = "https://thedraytonarmstheatre.co.uk/index.php"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".cbp-item"):
            title_el = card.css("h3").first
            if title_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            if not title:
                continue
            # Prefer the info anchor (second of two icon links) — the ticket
            # link points off-site.
            link_el = None
            for a in card.css("a[href]"):
                href = str(a.attrib.get("href", ""))
                if href.startswith("tickets/") or "tickets/" in href:
                    continue
                link_el = a
                break
            if link_el is None:
                link_el = card.css("a[href]").first
            if link_el is None:
                continue
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            # Dates live in the first <p> after the heading.
            start, end = (None, None)
            for p in card.css("p"):
                text = clean_text(p.get_all_text(separator=" ", strip=True))
                if text:
                    start, end = _parse_uk_ordinal(text)
                    break

            img_el = card.css("img").first
            image_url: str | None = None
            if img_el is not None:
                src = img_el.attrib.get("src") or img_el.attrib.get("data-src")
                if isinstance(src, str) and src and not src.startswith("data:"):
                    image_url = urllib.parse.urljoin(base_url, src)

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


def _parse_uk_ordinal(text: str) -> tuple[date | None, date | None]:
    """Parse `10th May 2026` or `10th May 2026 - 11th May 2026`."""
    matches = _UK_ORDINAL_DATE_RE.findall(text)
    dates: list[date] = []
    for d, m, y in matches:
        month = _MONTHS.get(m.lower())
        if month is None:
            continue
        try:
            dates.append(date(int(y), month, int(d)))
        except ValueError:
            continue
    if not dates:
        return None, None
    if len(dates) == 1:
        return dates[0], dates[0]
    return dates[0], dates[-1]
