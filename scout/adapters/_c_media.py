"""Shared parser for the Spektrix Vue.js `<div class="c-media c-media--event">`
listing pattern used by Donmar, Royal Court, Hackney Empire and others.

Each card renders the title in `<h3 class="c-media__title">`, dates as ISO
`<time itemprop="startDate"|"endDate">` pairs, optional description in
`<p class="c-media__summary">` and credits/subtitle in `.c-media__posttitle`.

The canonical URL hides in different places per venue:
  - Donmar / Hackney: a static `<a href="/events/<slug>">` inside the card.
  - Royal Court: the wrapper `<div>` carries `@click="goToUrl('https://...')"`.

The helper handles both — `<a href>` first, `@click` regex as fallback.
"""

from __future__ import annotations

import re
import urllib.parse
from datetime import date, datetime

from scrapling.parser import Selector

from scout.classify import classify
from scout.models import Show
from scout.text import clean_text

_GOTO_URL_RE = re.compile(r"goToUrl\(\s*['\"]([^'\"]+)['\"]")


def parse_c_media(
    html: str,
    base_url: str,
    *,
    theatre_slug: str,
    url_substring: str = "/events/",
) -> list[Show]:
    """Walk every `.c-media--event` on the page and return one `Show` per card.

    `url_substring` is a sanity filter on the chosen URL — e.g. `/events/` or
    `/productions/` — to reject stray nav links the @click fallback might pick.
    """
    page = Selector(html)
    seen: set[str] = set()
    shows: list[Show] = []
    for card in page.css(".c-media--event"):
        title_el = card.css(".c-media__title").first
        if title_el is None:
            continue
        title = clean_text(title_el.get_all_text(separator=" ", strip=True))
        if not title:
            continue

        url = _extract_url(card, base_url, url_substring)
        if url is None or url in seen:
            continue

        start, end = _extract_iso_dates(card)
        description = _extract_description(card)
        image_url = _extract_image(card, base_url)

        try:
            shows.append(
                Show(
                    theatre_slug=theatre_slug,
                    title=title,
                    show_type=classify(f"{title} {description}"),
                    url=url,
                    description=description,
                    start_date=start,
                    end_date=end,
                    image_url=image_url,
                )
            )
            seen.add(url)
        except Exception:
            continue
    return shows


def _extract_url(card: Selector, base_url: str, url_substring: str) -> str | None:
    """Donmar / Hackney expose a static `<a href>`; Royal Court only has a
    wrapper `@click="goToUrl('https://...')"`. Try both."""
    link_el = card.css(f'a[href*="{url_substring}"]').first
    if link_el is not None:
        href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
        if href:
            return urllib.parse.urljoin(base_url, href)

    click = card.attrib.get("@click")
    if isinstance(click, str):
        m = _GOTO_URL_RE.search(click)
        if m:
            href = m.group(1).split("#", 1)[0].split("?", 1)[0]
            if url_substring in href:
                return urllib.parse.urljoin(base_url, href)
    return None


def _extract_iso_dates(card: Selector) -> tuple[date | None, date | None]:
    def _parse(prop: str) -> date | None:
        el = card.css(f'time[itemprop="{prop}"]').first
        if el is None:
            return None
        raw = str(el.attrib.get("datetime", "")).strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            return None

    start = _parse("startDate")
    end = _parse("endDate")
    if start is not None and end is None:
        end = start
    return start, end


def _extract_description(card: Selector) -> str:
    summary = card.css(".c-media__summary").first
    if summary is None:
        return ""
    text = clean_text(summary.get_all_text(separator=" ", strip=True))
    # Trailing "…" indicates truncation in source — keep it; UI handles it fine.
    return text


def _extract_image(card: Selector, base_url: str) -> str | None:
    """Donmar serves four responsive variants per card; Royal Court / Hackney
    one img.o-image__img. Try the desktop variants first, fall back to any."""
    for sel in [".c-media__image-l img", ".c-media__image-m img", "img.o-image__img", "img"]:
        img = card.css(sel).first
        if img is None:
            continue
        src = img.attrib.get("src") or img.attrib.get("data-src")
        if isinstance(src, str) and src and not src.startswith("data:"):
            return urllib.parse.urljoin(base_url, src)
    return None
