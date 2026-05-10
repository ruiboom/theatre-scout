"""Eventim Apollo — generic `a[href*="/events/"]` matched the per-card
"Information" button so every row was titled "Information". Each `.card` has
the real title in `<h3 class="card__title">` plus a separate "Information"
anchor that supplies the canonical `/events/<slug>` URL.

  <div class="card card--horizontal">
    <div class="card__image"><img src="..." /></div>
    <div class="card__info">
      <p class="date uppercase">Wednesday 3rd June 2026</p>
      <h3 class="card__title">Jujutsu Kaisen in Concert</h3>
    </div>
    <a class="btn" href="/events/jujutsu-kaisen">Information</a>
  </div>
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
class EventimApolloAdapter(BaseAdapter):
    slug = "eventim-apollo"
    url = "https://www.eventimapollo.com/events/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for card in page.css(".card"):
            title_el = card.css(".card__title").first
            link_el = card.css('a[href*="/events/"]').first
            if title_el is None or link_el is None:
                continue
            title = clean_text(title_el.get_all_text(separator=" ", strip=True))
            href = str(link_el.attrib.get("href", "")).split("#", 1)[0].split("?", 1)[0]
            if not title or not href or href.endswith("/events/"):
                continue
            url = urllib.parse.urljoin(base_url, href)
            if url in seen:
                continue

            date_el = card.css(".date").first
            date_text = (
                clean_text(date_el.get_all_text(separator=" ", strip=True)) if date_el else ""
            )
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
                        theatre_slug=self.slug,
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
