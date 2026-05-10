from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.royal_court import RoyalCourtAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "royal-court.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return RoyalCourtAdapter().parse(
        FIXTURE.read_text(),
        "https://royalcourttheatre.com/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 3


def test_titles_are_real_not_more_info(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"more info", "book now", "details"}, s.title
        assert not low.startswith("more info "), s.title


def test_urls_are_event_pages_no_fragment(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Krapp" in t for t in titles), f"Krapp's Last Tape missing; got: {titles}"


def test_iso_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    krapp = next((s for t, s in by_title.items() if "Krapp" in t), None)
    assert krapp is not None
    assert krapp.start_date == date(2026, 5, 11)
    assert krapp.end_date == date(2026, 5, 30)
