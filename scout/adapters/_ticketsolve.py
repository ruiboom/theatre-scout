"""Shared parser for Ticketsolve / Ticketbooth listing and detail pages.

Several smaller venues route their `/whats-on/` link to a Ticketsolve subdomain
where the actual show listing lives behind a JS-rendered SPA. After stealth
fetch the listing pages all share the same DOM:

  <article class="show-card">
    <a href="/ticketbooth/shows/<id>"><h2>Title</h2></a>
    <img src="https://...cloudfront.../variants/..." />
    ... <span class="truncate">12 May 2026</span>
        <span>until</span>
        <span class="truncate">24 May 2026</span>  (optional — single-date if absent)
  </article>

Detail pages also need stealth and have the synopsis as one of several `<p>`
elements inside `<main>`; the first qualifying paragraph is usually the show
subtitle / credits, so we pick the longest non-boilerplate paragraph instead.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text, is_boilerplate

_DESC_MIN_CHARS = 60
_DESC_MAX_CHARS = 600


def parse_ticketsolve(html: str, base_url: str, *, theatre_slug: str) -> list[Show]:
    page = Selector(html)
    seen: set[str] = set()
    shows: list[Show] = []
    for card in page.css(".show-card"):
        title_el = card.css("h2").first
        link_el = card.css('a[href*="/ticketbooth/shows/"]').first
        if title_el is None or link_el is None:
            continue
        title = title_el.get_all_text(separator=" ", strip=True)
        if not title:
            continue
        href = str(link_el.attrib.get("href", "")).split("?", 1)[0]
        if not href:
            continue
        url = urllib.parse.urljoin(base_url, href)
        if url in seen:
            continue

        # Date spans live inside the card; "until — " sits between them as text
        # nodes that parse_date_range doesn't recognise. Replace with a hyphen
        # before parsing so a multi-day run gets caught as a real range.
        date_text = " ".join(
            s.get_all_text(separator=" ", strip=True) for s in card.css("span.truncate")
        )
        if " until " in f" {date_text} ":
            date_text = date_text.replace("until", "-")
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


def enrich_ticketsolve(html: str, base_url: str) -> dict[str, Any]:
    """Pull a synopsis from a Ticketsolve show detail page.

    The page DOM looks roughly like:
      <main>
        ... <p>Title — subtitle, credits</p>
        <p>One-line tagline.</p>
        <p>The actual plot synopsis (often the longest paragraph).</p>
        <p>Marketing pull-quotes...</p>
      </main>

    The first qualifying paragraph is usually the subtitle/credits, so we pick
    the longest substantive paragraph instead. Falls back to the generic image
    extractor for the hero image.
    """
    page = Selector(html)
    out: dict[str, Any] = {}

    main = page.css("main").first
    if main is not None:
        best = ""
        for p in main.find_all("p"):
            text = clean_text(p.get_all_text(separator=" ", strip=True))
            if len(text) < _DESC_MIN_CHARS or is_boilerplate(text):
                continue
            if len(text) > len(best):
                best = text
        if best:
            if len(best) > _DESC_MAX_CHARS:
                best = best[:_DESC_MAX_CHARS].rsplit(" ", 1)[0] + "…"
            out["description"] = best

    # Reuse the generic image extractor — Ticketsolve detail pages have a hero
    # img inside <main> that this picks up cleanly.
    from scout.enrich import extract_image

    img = extract_image(html, base_url)
    if img:
        out["image_url"] = img
    return out
