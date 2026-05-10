"""Shared parser for ATG (Ambassador Theatre Group) venue listings.

ATG runs a JS-rendered Next.js app for each venue: New Wimbledon, Richmond,
etc. After stealth render every show is a `<div data-testid="showCard">`
(MUI Card markup) containing:

  <a aria-hidden="true" href="/shows/<slug>/<venue-slug>/">
    <img alt="Title" src="..." />
  </a>
  <h2>Title</h2>                                     ← real title
  <p>Musicals</p>                                    ← genre
  <p>Venue Name</p>
  <p>Sat 23 May - Sat 30 May 2026</p>                ← dates
  <a href="/shows/<slug>/<venue-slug>/calendar/">    ← "Buy tickets for X" button
    <span>Buy tickets for Title</span>
  </a>

Generic adapter picked up the "Buy tickets for X" anchor as the title; we
walk the proper card structure instead.
"""

from __future__ import annotations

import re
import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from ._html import parse_date_range

_DATE_HINT_RE = re.compile(r"\d{1,2}\s+[A-Za-z]{3,}", re.IGNORECASE)


def parse_atg(html: str, base_url: str, *, theatre_slug: str, venue_slug: str) -> list[Show]:
    """`venue_slug` is the URL-segment ATG uses for the venue (e.g.
    `new-wimbledon-theatre`). We use it both to pick the right anchor and to
    skip stray `/shows/.../<other-venue>/` links that bleed in from related-
    venues sections."""
    page = Selector(html)
    seen: set[str] = set()
    shows: list[Show] = []
    for card in page.css('[data-testid="showCard"]'):
        title_el = card.css("h2").first
        if title_el is None:
            continue
        title = clean_text(title_el.get_all_text(separator=" ", strip=True))
        if not title:
            continue

        # The card contains 3+ /shows/ links per show (image, title-link,
        # "Buy tickets" calendar link, "More info" link). Pick a non-calendar
        # `/shows/<slug>/<venue>/` URL.
        url: str | None = None
        for a in card.css('a[href*="/shows/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or "/calendar/" in href or f"/{venue_slug}/" not in href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            break
        if url is None or url in seen:
            continue

        # Walk the card's <p> tags. Genre + venue + date are siblings, in that
        # order; we only need date + genre.
        genre = ""
        date_text = ""
        for p in card.css("p"):
            txt = clean_text(p.get_all_text(separator=" ", strip=True))
            if not txt:
                continue
            if not genre and not _looks_like_date(txt) and len(txt) < 30:
                genre = txt
            if _looks_like_date(txt) and not date_text:
                date_text = txt
                break
        start, end = parse_date_range(date_text)

        img_el = card.css("img").first
        image_url: str | None = None
        if img_el is not None:
            src = img_el.attrib.get("src") or img_el.attrib.get("data-src")
            if isinstance(src, str) and src and not src.startswith("data:"):
                image_url = urllib.parse.urljoin(base_url, src)

        try:
            shows.append(
                Show(
                    theatre_slug=theatre_slug,
                    title=title,
                    show_type=classify(f"{title} {genre}"),
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


def _looks_like_date(text: str) -> bool:
    return bool(_DATE_HINT_RE.search(text))
