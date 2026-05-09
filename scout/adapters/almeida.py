from __future__ import annotations

import urllib.parse

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class AlmeidaAdapter(BaseAdapter):
    slug = "almeida"
    url = "https://almeida.co.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        shows: list[Show] = []
        for card in page.css(".c-event-card__wrapper"):
            title_el = card.css("h3.c-event-card__title").first
            link_el = card.css("a[href]").first
            img_el = card.css("img").first
            if title_el is None or link_el is None:
                continue
            title = title_el.get_all_text(separator=" ", strip=True)
            url = urllib.parse.urljoin(base_url, str(link_el.attrib.get("href", "")))
            text = card.get_all_text(separator=" ", strip=True)
            start, end = parse_date_range(text)
            image = str(img_el.attrib.get("src", "")) if img_el is not None else ""
            shows.append(
                Show(
                    theatre_slug=self.slug,
                    title=title,
                    show_type="play",
                    url=url,
                    start_date=start,
                    end_date=end,
                    image_url=image or None,
                )
            )
        return shows
