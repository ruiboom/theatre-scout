"""Spektrix API adapters (Donmar Warehouse, Royal Court).

Fixtures are trimmed captures of the real v3 `events` feeds (2026-07): a few
productions plus one of each junk species the filters must reject — member
events, tours, tastings, open technical sessions and Spektrix test entries.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scrapers.adapters import _spektrix
from scrapers.adapters.donmar_warehouse import _keep as donmar_keep
from scrapers.adapters.donmar_warehouse import _make_url as donmar_make_url
from scrapers.adapters.royal_court import _in_auditorium

FIXTURES = Path(__file__).parent / "fixtures"
# Both fixtures were captured on this date; using it as "today" keeps every
# event's run in the future forever.
TODAY = date(2026, 7, 1)


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_donmar_keeps_only_productions() -> None:
    shows = _spektrix.parse_events(
        _load("donmar_spektrix_events.json"),
        theatre_slug="donmar-warehouse",
        keep=donmar_keep,
        make_url=donmar_make_url,
        today=TODAY,
    )
    titles = {s.title for s in shows}
    assert titles == {"A Month in the Country", "The King's Ransom", "No Man's Land"}


def test_donmar_show_fields() -> None:
    shows = _spektrix.parse_events(
        _load("donmar_spektrix_events.json"),
        theatre_slug="donmar-warehouse",
        keep=donmar_keep,
        make_url=donmar_make_url,
        today=TODAY,
    )
    by_title = {s.title: s for s in shows}
    ransom = by_title["The King's Ransom"]
    # CMS slug: apostrophe vanishes rather than hyphenating.
    assert ransom.url == "https://www.donmarwarehouse.com/events/the-kings-ransom"
    month = by_title["A Month in the Country"]
    assert month.start_date == date(2026, 8, 22)
    assert month.end_date == date(2026, 10, 3)


def test_royal_court_auditorium_filter() -> None:
    events = json.loads(_load("royal_court_spektrix_events.json"))
    kept = {e["name"] for e in events if _in_auditorium(e)}
    # Bar, tour and Zoom events go; everything staged in a Jerwood auditorium
    # stays (one-offs are filtered later by instance count, not here).
    assert "Backstage Tour" not in kept
    assert "Cazcabel Tequila Tasting at The Bar Below" not in kept
    assert "Writers' Card: Career Surgeries (in-person)" not in kept
    assert {"Archduke", "Man to Man", "Monument", "The Afronauts"} <= kept


def test_royal_court_instance_count_floor() -> None:
    events = json.loads(_load("royal_court_spektrix_events.json"))
    ids = {e["name"]: e["id"] for e in events}
    instances = json.dumps(
        [{"event": {"id": ids["Man to Man"]}}] * 55
        + [{"event": {"id": ids["Open Technical Session for Archduke"]}}]
        + [{"event": {"id": ids["Supercool test event"]}}] * 5
    )
    counts = _spektrix.instance_counts(instances)
    floor = 6
    survivors = {e["name"] for e in events if _in_auditorium(e) and counts[str(e["id"])] >= floor}
    assert survivors == {"Man to Man"}


def test_past_events_dropped() -> None:
    shows = _spektrix.parse_events(
        _load("royal_court_spektrix_events.json"),
        theatre_slug="royal-court",
        keep=_in_auditorium,
        make_url=lambda e: "https://royalcourttheatre.com/whats-on/",
        today=date(2026, 8, 1),  # Archduke closed 25 July
    )
    assert "Archduke" not in {s.title for s in shows}


def test_display_title_leaves_mixed_case_alone() -> None:
    assert _spektrix.display_title("John Proctor is the Villain") == ("John Proctor is the Villain")
    assert _spektrix.display_title("A MONTH IN THE COUNTRY") == "A Month in the Country"
