"""Donmar Warehouse — reads the venue's public Spektrix API.

donmarwarehouse.com hard-403s GitHub Actions' IP ranges: the fast path was
blocked first, and the stealth-browser fallback (2026-06) turned out to be
blocked at the same layer, so every cron scrape failed. The Spektrix events
feed is the same data the site's own front-end renders, minus the WAF — see
`_spektrix.py` for the trade-offs.

Productions are the events whose `attribute_AccountCode` sits under the
`10000/102/` ledger prefix; member events, script conversations and Spektrix
test entries have other codes or none. Show URLs use the site's CMS slug
pattern (`/events/<slugified-name>`), which matches every current production.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..models import Show
from . import _spektrix
from .base import BaseAdapter, _ClientLike
from .registry import register

_PRODUCTION_ACCOUNT_PREFIX = "10000/102/"


def _keep(event: dict[str, Any]) -> bool:
    return str(event.get("attribute_AccountCode") or "").startswith(_PRODUCTION_ACCOUNT_PREFIX)


def _make_url(event: dict[str, Any]) -> str:
    slug = _spektrix.event_page_slug(str(event.get("name") or ""))
    return f"https://www.donmarwarehouse.com/events/{slug}"


@register
class DonmarWarehouseAdapter(BaseAdapter):
    slug = "donmar-warehouse"
    url = _spektrix.events_url("donmarwarehouse")
    requires_js = False

    def fetch(self, client: _ClientLike) -> list[Show]:
        # ignore_robots: system.spektrix.com blanket-Disallows crawlers, but the
        # v3 API is its documented public integration surface — see Client.get.
        text = self._response_text(client.get(self.url, ignore_robots=True))
        return self.parse(text, self.url)

    def parse(self, html: str, base_url: str) -> list[Show]:
        return _spektrix.parse_events(
            html,
            theatre_slug=self.slug,
            keep=_keep,
            make_url=_make_url,
            today=date.today(),
        )
