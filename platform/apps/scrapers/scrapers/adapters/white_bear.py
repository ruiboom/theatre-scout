"""White Bear Theatre — JS-rendered Wix site. The homepage at the root URL
just shows a slide-show of the current production; the actual programme
lives at `/whatson` as a Wix gallery.

Each show is a `<a href="/whatson/<slug>">` wrapping an `<img alt="Title">`,
with date strings appearing in separate `[role="listitem"]` elements that
aren't structurally tied to the gallery anchor. We capture title + URL +
image; dates would need detail-page enrichment to be reliable.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter
from .registry import register


@register
class WhiteBearAdapter(BaseAdapter):
    slug = "white-bear"
    url = "https://www.whitebeartheatre.co.uk/whatson"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('a[href*="/whatson/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or href.rstrip("/").endswith("/whatson"):
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue
            img = a.css("img").first
            if img is None:
                continue
            alt = clean_text(str(img.attrib.get("alt", "")))
            if not alt:
                continue
            src = img.attrib.get("src") or img.attrib.get("data-src")
            image_url: str | None = None
            if isinstance(src, str) and src and not src.startswith("data:"):
                image_url = urllib.parse.urljoin(base_url, src)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=alt,
                        show_type=classify(alt),
                        url=url,
                        image_url=image_url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows
