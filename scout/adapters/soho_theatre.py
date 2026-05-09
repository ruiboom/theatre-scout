"""Soho Theatre — bespoke because (a) the listing paginates with WordPress-style
`/dean-street/page/N/` URLs and (b) the generic adapter's `a[href*="/events/"]`
selector grabs the entire card link text — venue badge ("Soho") + title + date
+ time + location + price, all squashed into one string.

Listing structure per card:
  <div class="card card--event">
    <a class="card-link" href="/events/<slug>/">
      <div class="card-image"><div class="image" data-back="<img-url>">
        <span class="card-tag">Soho</span>   ← venue badge, NOT title
      </div></div>
      <div class="card-content">
        <h3 class="card-title">Title</h3>
        <span class="subtitle">By Author<br>Directed by ...</span>
        <span class="date">Sat 9 May – Sat 6 Jun 26</span>
        <span class="price">From £15</span>
      </div>
    </a>
  </div>

Pagination: a `<a class="pagination-button" href=".../page/N+1/">Load more</a>`
appears at the bottom while there's a next page; absent on the final page.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import date

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter, _ClientLike
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

log = logging.getLogger(__name__)

# Hard cap so a runaway pagination loop never burns through hundreds of pages.
_MAX_PAGES = 20

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )
}

# "Sat 9 May 26" or "Sat 9 May – Sat 6 Jun 26" (en-dash); year is 2-digit.
_DATE_RE = re.compile(
    r"(?:[A-Z][a-z]{2}\s+)?"  # optional weekday
    r"(\d{1,2})\s+"  # day
    r"([A-Z][a-z]{2})"  # month abbrev
    r"(?:\s+(\d{2}))?"  # optional 2-digit year
)
_PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{1,2})?)")


@register
class SohoTheatreAdapter(BaseAdapter):
    slug = "soho-theatre"
    url = "https://sohotheatre.com/dean-street/"

    def fetch(self, client: _ClientLike) -> list[Show]:
        seen_urls: set[str] = set()
        shows: list[Show] = []
        next_url: str | None = self.url
        for _ in range(_MAX_PAGES):
            if next_url is None:
                break
            resp = client.get(next_url)
            if resp is None:
                break
            text = getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
                "utf-8", errors="replace"
            )
            page_shows, next_url = self._parse_page(text, next_url)
            for s in page_shows:
                if str(s.url) in seen_urls:
                    continue
                seen_urls.add(str(s.url))
                shows.append(s)
        return shows

    def parse(self, html: str, base_url: str) -> list[Show]:
        # Pure-parser entry point used by tests; pagination logic stays in fetch().
        return self._parse_page(html, base_url)[0]

    def _parse_page(self, html: str, base_url: str) -> tuple[list[Show], str | None]:
        page = Selector(html)
        out: list[Show] = []
        seen: set[str] = set()
        for card in page.css(".card--event"):
            show = self._card_to_show(card, base_url)
            if show is None or str(show.url) in seen:
                continue
            seen.add(str(show.url))
            out.append(show)
        next_btn = page.css("a.pagination-button").first
        next_href = str(next_btn.attrib.get("href", "")) if next_btn is not None else ""
        next_url = urllib.parse.urljoin(base_url, next_href.split("#", 1)[0]) if next_href else None
        return out, next_url

    def _card_to_show(self, card: Selector, base_url: str) -> Show | None:
        title_el = card.css(".card-title").first
        link_el = card.css("a.card-link").first
        if title_el is None or link_el is None:
            return None
        title = clean_text(title_el.get_all_text(separator=" ", strip=True))
        href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
        if not title or not href:
            return None
        url = urllib.parse.urljoin(base_url, href)

        subtitle_el = card.css(".subtitle").first
        subtitle = (
            clean_text(subtitle_el.get_all_text(separator=" ", strip=True)) if subtitle_el else ""
        )

        date_el = card.css(".date").first
        start, end = _parse_dates(
            clean_text(date_el.get_all_text(separator=" ", strip=True)) if date_el else ""
        )

        price_el = card.css(".price").first
        price_min = _parse_price(price_el.get_all_text(strip=True) if price_el else "")

        image_url = _extract_image(card, base_url)

        try:
            return Show(
                theatre_slug=self.slug,
                title=title,
                show_type=classify(f"{title} {subtitle}"),
                url=url,
                description=subtitle,
                start_date=start,
                end_date=end,
                price_min=price_min,
                image_url=image_url,
            )
        except Exception:
            return None


def _parse_dates(text: str) -> tuple[date | None, date | None]:
    """Parse "Sat 9 May 26" or "Sat 9 May – Sat 6 Jun 26".

    The end half always carries the year; the start half inherits it. Year is
    2-digit so we always assume 20YY (Soho lists upcoming shows, not history).
    """
    # Regex always captures day + month; year group is optional and surfaces as
    # an empty string when missing.
    matches: list[tuple[str, str, str]] = _DATE_RE.findall(text)
    if not matches:
        return None, None
    end_d, end_m, end_y = matches[-1]
    end_year = 2000 + int(end_y) if end_y else None
    end_date = _safe(end_year, _MONTHS.get(end_m), int(end_d))
    if len(matches) == 1:
        return end_date, end_date
    start_d, start_m, start_y = matches[0]
    start_year = 2000 + int(start_y) if start_y else end_year
    start_date = _safe(start_year, _MONTHS.get(start_m), int(start_d))
    return start_date, end_date


def _safe(year: int | None, month: int | None, day: int) -> date | None:
    if year is None or month is None:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_price(text: str) -> int | None:
    """`From £15` → 1500 pence."""
    m = _PRICE_RE.search(text)
    if not m:
        return None
    pence = int(round(float(m.group(1)) * 100))
    return pence if pence > 0 else None


def _extract_image(card: Selector, base_url: str) -> str | None:
    """Soho lazy-loads via `data-back="<url>"` on a sibling div, not src on img."""
    img_holder = card.css(".card-image .image").first
    if img_holder is not None:
        src = img_holder.attrib.get("data-back") or img_holder.attrib.get("data-src")
        if isinstance(src, str) and src and not src.startswith("data:"):
            return urllib.parse.urljoin(base_url, src)
    img = card.css("img").first
    if img is not None:
        src = img.attrib.get("src") or img.attrib.get("data-src")
        if isinstance(src, str) and src and not src.startswith("data:"):
            return urllib.parse.urljoin(base_url, src)
    return None
