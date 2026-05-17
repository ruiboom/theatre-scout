"""Minimal best-effort listings parser for JavaScript-rendered venue sites.

Some venues (Wix, Jimdo, other site builders) render their programme entirely
client-side, so they are fetched with the stealth browser
(`requires_js = True`). Their CSS class names are auto-generated hashes, so the
only durable hooks are structured data (`application/ld+json`) and the event
detail anchors the builder emits (e.g. Wix Events' `/event-details/<slug>`).

This helper tries JSON-LD first, then sweeps for those anchors, deriving the
title from the link text or a wrapped image's `alt`. It deliberately returns
``[]`` rather than guessing when a render yields nothing — partial data beats
junk, and the venue still appears in the directory either way.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from scout.adapters._jsonld import parse_jsonld
from scout.classify import classify
from scout.models import Show, ShowType
from scout.text import clean_text

# Anchor text that is a call-to-action, not a show title.
_SKIP = {
    "more info",
    "book now",
    "buy now",
    "buy tickets",
    "book tickets",
    "read more",
    "read more »",
    "tickets",
    "what's on",
    "what’s on",
}


def parse_js_listings(
    html: str,
    base_url: str,
    slug: str,
    *,
    default_type: ShowType = "play",
    href_contains: tuple[str, ...] = ("/event-details/",),
) -> list[Show]:
    """JSON-LD events if present, else event-detail anchors. Never raises."""
    shows = parse_jsonld(html, theatre_slug=slug, base_url=base_url)
    if shows:
        return shows

    page = Selector(html)
    selector = ", ".join(f'a[href*="{frag}"]' for frag in href_contains)
    seen: set[str] = set()
    out: list[Show] = []
    for a in page.css(selector):
        href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
        if not href:
            continue
        url = urllib.parse.urljoin(base_url, href)
        if url in seen:
            continue
        title = clean_text(a.get_all_text(separator=" ", strip=True))
        if not title:
            img = a.css("img").first
            if img is not None:
                title = clean_text(str(img.attrib.get("alt", "")))
        if not title or len(title) > 200 or title.lower() in _SKIP:
            continue
        try:
            out.append(
                Show(
                    theatre_slug=slug,
                    title=title,
                    show_type=classify(title, default=default_type),
                    url=url,
                )
            )
            seen.add(url)
        except Exception:
            continue
    return out
