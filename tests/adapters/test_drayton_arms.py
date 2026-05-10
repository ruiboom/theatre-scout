from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.drayton_arms import DraytonArmsAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "drayton-arms.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return DraytonArmsAdapter().parse(
        FIXTURE.read_text(),
        "https://thedraytonarmstheatre.co.uk/index.php",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "tickets", "info"}, s.title


def test_urls_are_unique_and_not_tickets(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "tickets/" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "The Full English" in titles, f"missing; got: {titles}"


def test_uk_ordinal_dates(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    fe = by_title.get("The Full English")
    assert fe is not None
    # Listing said "10th May 2026 - 11th May 2026"
    assert fe.start_date == date(2026, 5, 10)
    assert fe.end_date == date(2026, 5, 11)
