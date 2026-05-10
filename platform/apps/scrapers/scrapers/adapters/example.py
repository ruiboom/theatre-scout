"""
Example adapter — copy this file when adding a new venue.

The shape of this file is the contract: subclass BaseAdapter, set the slug
and homepage, implement fetch(). Yield ScrapedShow instances. The orchestrator
handles writes, error recording, and rate-limiting per host.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from ..base import BaseAdapter
from ..models import ScrapedPerformance, ScrapedShow


class ExampleAdapter(BaseAdapter):
    slug = "example"
    name = "Example Venue"
    homepage = "https://example.com/"

    def fetch(self) -> Iterable[ScrapedShow]:
        # In a real adapter:
        #   from ..http import Http
        #   from bs4 import BeautifulSoup
        #   html = Http().get(f"{self.homepage}whats-on")
        #   soup = BeautifulSoup(html, "lxml")
        #   for card in soup.select(".show-card"): yield self._parse(card)

        # For the scaffold: a single deterministic fixture so the pipeline
        # can be smoke-tested end-to-end without network.
        yield ScrapedShow(
            venue_slug=self.slug,
            slug="example-show",
            title="An Example Show",
            description_short="A placeholder show emitted by the example adapter.",
            description_full=(
                "This is a stub. Replace ExampleAdapter.fetch() with a real "
                "implementation that scrapes a venue's listings page."
            ),
            price_min_pence=1000,
            price_max_pence=2000,
            booking_url="https://example.com/book",
            genres=["play"],
            tags=["scaffold"],
            performances=[
                ScrapedPerformance(
                    starts_at=datetime.utcnow().replace(microsecond=0)
                    + timedelta(days=2, hours=19),
                ),
            ],
        )
