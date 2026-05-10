from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.sadlers_wells import SadlersWellsAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sadlers-wells.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return SadlersWellsAdapter().parse(
        FIXTURE.read_text(),
        "https://www.sadlerswells.com/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_get_tickets(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert "get tickets" not in low, s.title
        assert low not in {"book now", "more info", "tickets"}, s.title


def test_urls_are_canonical_event_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/whats-on/" in u and not u.endswith("/whats-on/"), u


def test_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    with_dates = [s for s in shows if s.start_date is not None]
    assert len(with_dates) / len(shows) >= 0.8


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("YAMATO" in t for t in titles), f"YAMATO missing; got: {titles}"


def test_known_date_range(shows) -> None:  # type: ignore[no-untyped-def]
    yamato = next((s for s in shows if "YAMATO" in s.title), None)
    assert yamato is not None
    # Listing said "12 – 30 May 2026"
    assert yamato.start_date == date(2026, 5, 12)
    assert yamato.end_date == date(2026, 5, 30)
