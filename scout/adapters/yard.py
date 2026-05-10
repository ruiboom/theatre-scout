"""The Yard Theatre — JS-rendered Next.js listing. Markup uses Tailwind utility
classes only (no semantic event-card class), so we can't query a card class.

Structure per show (after stealth render):

  <li class="col-span-... ...">
    <a href="/events/<slug>">
      <img alt="Cover image for Title" srcset="..." />
    </a>
    <div class="space-y-3 my-4">
      <h5>Theatre</h5>                    ← genre / category
      <h2 class="my-2">Title</h2>
      <h4>14 July - 25 July 2026</h4>
      <a class="btn" href="/events/<slug>/tickets/SODA">Book now</a>
    </div>
  </li>

We scope on `<li>` elements that contain an `<a href="/events/...">` and an
`<h2>`, then read the children. Filter out `/tickets/` links so we keep the
canonical show URL.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text


@register
class YardAdapter(BaseAdapter):
    slug = "yard"
    url = "https://www.theyardtheatre.co.uk/whats-on"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for li in page.css("li"):
            title_el = li.css("h2").first
            if title_el is None:
                continue
            link_el: Selector | None = None
            for a in li.css('a[href*="/events/"]'):
                href = str(a.attrib.get("href", ""))
                if "/tickets/" not in href:
                    link_el = a
                    break
            if link_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            date_el = li.css("h4").first
            date_text = (
                clean_text(date_el.get_all_text(separator=" ", strip=True)) if date_el else ""
            )
            start, end = parse_date_range(date_text)

            genre_el = li.css("h5").first
            genre = genre_el.get_all_text(strip=True) if genre_el else ""

            image_url = _extract_image(li, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
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


def _extract_image(card: Selector, base_url: str) -> str | None:
    """Yard uses Next.js Image, which serves a `/_next/image?url=<encoded>` src.
    Decode the wrapped URL so we link to the underlying CDN asset."""
    img = card.css("img").first
    if img is None:
        return None
    src = img.attrib.get("src") or img.attrib.get("data-src")
    if not isinstance(src, str) or not src or src.startswith("data:"):
        return None
    full = urllib.parse.urljoin(base_url, src)
    parsed = urllib.parse.urlparse(full)
    if parsed.path.endswith("/_next/image"):
        params = urllib.parse.parse_qs(parsed.query)
        wrapped = params.get("url", [None])[0]
        if wrapped:
            return urllib.parse.unquote(wrapped)
    return full
