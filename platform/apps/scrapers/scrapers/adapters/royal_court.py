"""Royal Court — reads the venue's public Spektrix API.

royalcourttheatre.com hard-403s GitHub Actions' IP ranges (stealth browser
included), so the cron could never load the listing — see `_spektrix.py` for
why the Spektrix feed is the venue-approved way around that.

Productions are events staged in a Jerwood Theatre auditorium
(`attribute_TicketVenue1`) with a meaningful run still ahead of them: one-offs
sharing the auditorium (open technical sessions, award nights, Spektrix test
entries) all have ≤5 remaining performances, while the shortest real run books
dozens, so the instance-count floor separates them cleanly. Counting *remaining*
instances means a production can drop off in its final days — acceptable, it is
nearly closed by then.

The site's per-show URLs aren't derivable from event names (e.g. "The
Afronauts" lives at `/events/afronauts`, "John Proctor is the Villain" at
`/events/john-proctor-is-the-villain-west-end`), so shows link to the What's On
listing instead of a guessed 404.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from ..models import Show
from . import _spektrix
from .base import BaseAdapter, _ClientLike
from .registry import register

_CLIENT = "royalcourt"
_LISTING_URL = "https://royalcourttheatre.com/whats-on/"
_AUDITORIUM_PREFIX = "Jerwood Theatre"
_MIN_REMAINING_INSTANCES = 6


def _in_auditorium(event: dict[str, Any]) -> bool:
    return str(event.get("attribute_TicketVenue1") or "").startswith(_AUDITORIUM_PREFIX)


@register
class RoyalCourtAdapter(BaseAdapter):
    slug = "royal-court"
    url = _spektrix.events_url(_CLIENT)
    requires_js = False

    def fetch(self, client: _ClientLike) -> list[Show]:
        # ignore_robots: system.spektrix.com blanket-Disallows crawlers, but the
        # v3 API is its documented public integration surface — see Client.get.
        events_text = self._response_text(client.get(self.url, ignore_robots=True))
        inst_url = _spektrix.instances_url(_CLIENT, start_from=date.today())
        instances_text = self._response_text(client.get(inst_url, ignore_robots=True), url=inst_url)
        counts = _spektrix.instance_counts(instances_text)

        def keep(event: dict[str, Any]) -> bool:
            return (
                _in_auditorium(event) and counts[str(event.get("id"))] >= _MIN_REMAINING_INSTANCES
            )

        return self._build(events_text, keep)

    def parse(self, html: str, base_url: str) -> list[Show]:
        # Events feed alone (no instance counts): auditorium filter only. Kept
        # for the (html, url) -> shows contract; fetch() adds the count floor.
        return self._build(html, _in_auditorium)

    def _build(self, events_text: str, keep: Callable[[dict[str, Any]], bool]) -> list[Show]:
        return _spektrix.parse_events(
            events_text,
            theatre_slug=self.slug,
            keep=keep,
            make_url=lambda e: _LISTING_URL,
            today=date.today(),
        )
