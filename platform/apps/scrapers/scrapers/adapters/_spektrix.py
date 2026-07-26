"""Shared parser for the Spektrix v3 REST API.

Donmar Warehouse and the Royal Court both sell through Spektrix, and both
venues' WAFs hard-403 GitHub Actions' IP ranges — the stealth browser included
— so their own listing pages are unreachable from the daily cron. The Spektrix
API (`https://system.spektrix.com/<client>/api/v3/...`) is the venue-approved
integration surface their own front-ends call: public, JSON, unauthenticated
for reads, and not behind the venue WAF. We read `events` (and, where needed,
`instances` for per-event performance counts) and build Shows from that.

The events feed mixes real productions with tours, workshops, member events and
ticketing-system test entries, so each adapter supplies a `keep` predicate
tuned to signals in its venue's data (account codes, ticket-venue attributes,
instance counts).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from ..classify import classify
from ..models import Show
from ..text import clean_text

_APOSTROPHE_RE = re.compile(r"['’]")

#: Words kept lowercase when de-shouting an ALL-CAPS title (unless first/last).
_SMALL_WORDS = {"a", "an", "and", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to"}


def events_url(client_name: str) -> str:
    return f"https://system.spektrix.com/{client_name}/api/v3/events"


def instances_url(client_name: str, *, start_from: date) -> str:
    return (
        f"https://system.spektrix.com/{client_name}/api/v3/instances"
        f"?start_from={start_from.isoformat()}"
    )


def display_title(name: str) -> str:
    """De-shout an ALL-CAPS event name ("NO MAN'S LAND" → "No Man's Land").

    Mixed-case names pass through untouched — only names the box office typed
    in caps get rewritten, so venues that case their titles keep them.
    """
    cleaned = clean_text(name)
    if cleaned != cleaned.upper():
        return cleaned
    words = cleaned.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        keep_lower = 0 < i < len(words) - 1 and w in _SMALL_WORDS
        out.append(w if keep_lower else w[:1].upper() + w[1:])
    return " ".join(out)


def event_page_slug(name: str) -> str:
    """Venue-CMS-style slug for an event name: apostrophes vanish rather than
    hyphenate ("THE KING'S RANSOM" → "the-kings-ransom"), everything else as
    `text.slugify`."""
    from ..text import slugify

    return slugify(_APOSTROPHE_RE.sub("", name))


def _event_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def instance_counts(instances_json: str) -> Counter[str]:
    """Instances payload → {event id: number of performances}."""
    counts: Counter[str] = Counter()
    for inst in json.loads(instances_json):
        event = inst.get("event") or {}
        event_id = event.get("id") if isinstance(event, dict) else None
        if event_id:
            counts[str(event_id)] += 1
    return counts


def parse_events(
    events_json: str,
    *,
    theatre_slug: str,
    keep: Callable[[dict[str, Any]], bool],
    make_url: Callable[[dict[str, Any]], str],
    today: date,
) -> list[Show]:
    """Build one Show per kept event. Events whose run has already ended are
    dropped (the feed keeps recently closed shows around for a while)."""
    shows: list[Show] = []
    for event in json.loads(events_json):
        if not keep(event):
            continue
        start = _event_date(event.get("firstInstanceDateTime"))
        end = _event_date(event.get("lastInstanceDateTime"))
        if end is not None and end < today:
            continue
        title = display_title(str(event.get("name") or ""))
        if not title:
            continue
        image = str(event.get("imageUrl") or "") or None
        try:
            shows.append(
                Show(
                    theatre_slug=theatre_slug,
                    title=title,
                    show_type=classify(title, default="play"),
                    description=clean_text(str(event.get("description") or "")),
                    url=make_url(event),
                    start_date=start,
                    end_date=end,
                    duration_minutes=int(event.get("duration") or 0) or None,
                    image_url=image,
                    raw={"spektrix_id": event.get("id")},
                )
            )
        except Exception:
            continue
    return shows
