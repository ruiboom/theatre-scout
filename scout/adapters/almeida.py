from __future__ import annotations

import urllib.parse

from bs4 import BeautifulSoup

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.models import Show


@register
class AlmeidaAdapter(BaseAdapter):
    slug = "almeida"
    url = "https://almeida.co.uk/whats-on/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        soup = BeautifulSoup(html, "lxml")
        shows: list[Show] = []
        for card in soup.select(".c-event-card__wrapper"):
            title_el = card.select_one("h3.c-event-card__title")
            link_el = card.find("a", href=True)
            img_el = card.find("img")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(" ", strip=True)
            url = urllib.parse.urljoin(base_url, str(link_el["href"]))
            text = card.get_text(" ", strip=True)
            start, end = parse_date_range(text)
            image = str(img_el.get("src", "")) if img_el else ""
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
