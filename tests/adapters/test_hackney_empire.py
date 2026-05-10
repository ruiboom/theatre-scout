from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.hackney_empire import HackneyEmpireAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "hackney-empire.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return HackneyEmpireAdapter().parse(
        FIXTURE.read_text(),
        "https://www.hackneyempire.co.uk/whats-on",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_button_text(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"details", "book now", "more info", "tickets"}, s.title


def test_urls_are_event_pages_no_fragment(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "Noughts and Crosses" in titles, f"missing; got: {titles}"


def test_iso_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    nc = by_title.get("Noughts and Crosses")
    assert nc is not None
    assert nc.start_date == date(2026, 5, 12)
    assert nc.end_date == date(2026, 5, 14)
