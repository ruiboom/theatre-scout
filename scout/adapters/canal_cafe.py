"""Canal Cafe Theatre, Little Venice — long-running comedy/cabaret room above
the Bridge House pub (home of NewsRevue). The /our-shows/ page is a WPBakery
grid where each production is a `div.showbox` holding only meta fields — show
name, run string, price — with no per-show page. We use the listings URL as
the canonical link, keep the run string as the description, and best-effort
parse dates out of it (often year-less, so usually left null).
"""

from __future__ import annotations

from scrapling.parser import Selector

from scout.adapters._html import parse_date_range
from scout.adapters.base import BaseAdapter
from scout.adapters.registry import register
from scout.classify import classify
from scout.models import Show
from scout.text import clean_text


@register
class CanalCafeAdapter(BaseAdapter):
    slug = "canal-cafe"
    url = "https://canalcafetheatre.com/our-shows/"

    def parse(self, html: str, base_url: str) -> list[Show]:
        page = Selector(html)
        seen: set[str] = set()
        shows: list[Show] = []
        for box in page.css("div.showbox"):
            name_el = box.css(".vc_gitem-post-meta-field-show_name").first
            if name_el is None:
                continue
            title = clean_text(name_el.get_all_text(separator=" ", strip=True))
            key = title.lower()
            if not title or key in seen:
                continue
            run_el = box.css(".vc_gitem-post-meta-field-duration").first
            run = (
                clean_text(run_el.get_all_text(separator=" ", strip=True))
                if run_el is not None
                else ""
            )
            start, end = parse_date_range(run)
            try:
                shows.append(
                    Show(
                        theatre_slug=self.slug,
                        title=title,
                        show_type=classify(f"{title} {run}", default="comedy"),
                        url=base_url,
                        description=run,
                        start_date=start,
                        end_date=end,
                    )
                )
                seen.add(key)
            except Exception:
                continue
        return shows
