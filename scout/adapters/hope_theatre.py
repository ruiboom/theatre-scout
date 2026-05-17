"""The Hope Theatre, Islington — Wix site (JS-rendered, so requires_js).

Each show on /what-s-on is a hand-placed Wix block: a 22px rich-text heading
(title), a 20px heading (date), then an "INFORMATION" button linking to the
show's own page (thehopetheatre.com/<slug>) and a "TICKETS" button to
TicketSource. Wix class names are hashed, so we key off the stable
`aria-label="INFORMATION"` anchors and the template's inline title font-size,
pairing them in document order.
"""

from __future__ import annotations

from scrapling.parser import Selector

from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text


@register
class HopeTheatreAdapter(BaseAdapter):
    slug = "hope-theatre"
    url = "https://www.thehopetheatre.com/what-s-on"
    requires_js = True

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)

        info_urls: list[str] = []
        for a in page.css('a[aria-label="INFORMATION"]'):
            href = str(a.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if "thehopetheatre.com/" in href and not href.rstrip("/").endswith("what-s-on"):
                info_urls.append(href)

        titles: list[str] = []
        for h in page.css("h5.font_5"):
            style = str(h.attrib.get("style", ""))
            if "font-size:22px" not in style.replace(" ", ""):
                continue
            text = clean_text(h.get_all_text(separator=" ", strip=True))
            if text and text not in titles:
                titles.append(text)

        shows: list[Show] = []
        seen: set[str] = set()
        for title, url in zip(titles, info_urls, strict=False):
            if not title or len(title) > 200 or url in seen:
                continue
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(title),
                        url=url,
                    )
                )
                seen.add(url)
            except Exception:
                continue
        return shows
