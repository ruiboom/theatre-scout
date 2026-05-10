"""Old Red Lion Pub & Playhouse — the homepage at `weareoldred.co.uk/` is a
brand splash with no event list; the actual programme lives at `/whats-on/`.
The page is a simple WordPress block layout with each show as:

  <p class="has-text-align-center">
    <strong><a href="/whats-on/<slug>/" data-type="page">Title</a></strong>
  </p>
  <figure class="wp-block-image">
    <a href="/whats-on/<slug>/"><img src="..." /></a>
  </figure>

No dates on the listing — would need detail-page enrichment to fill those in.
"""

from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show
from ..text import clean_text
from .base import BaseAdapter
from .registry import register

_NON_SHOW_SLUGS = {"club", "feed", "ical"}


@register
class OldRedLionAdapter(BaseAdapter):
    slug = "old-red-lion"
    url = "https://weareoldred.co.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for a in page.css('p.has-text-align-center > strong > a[href*="/whats-on/"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not href or href.rstrip("/").endswith("/whats-on"):
                continue
            slug = href.rstrip("/").rsplit("/", 1)[-1]
            if slug in _NON_SHOW_SLUGS:
                continue
            title = clean_text(a.get_all_text(separator=" ", strip=True))
            if not title:
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            image_url = _find_image_for(a, base_url)

            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=url,
                        image_url=image_url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows


def _find_image_for(anchor: Selector, base_url: str) -> str | None:
    """Walk forward in the page tree to the next `<figure>` containing an `<img>`
    that links to the same show URL. Squarespace, WordPress, etc. all use a
    "title paragraph then poster figure" pattern here; we don't need to be
    precise — any image in the same parent works."""
    parent = anchor.parent
    while parent is not None:
        for img in parent.css("img"):
            src = img.attrib.get("src") or img.attrib.get("data-src")
            if isinstance(src, str) and src and not src.startswith("data:"):
                return urllib.parse.urljoin(base_url, src)
        # only walk up once — beyond that we'd grab the page logo
        parent = None
    return None
