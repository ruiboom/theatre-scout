from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.etcetera import EtceteraAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "etcetera.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return EtceteraAdapter().parse(
        FIXTURE.read_text(),
        "https://www.etceteratheatrecamden.com/events/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    # Etcetera lists every fringe-night gig — there are dozens.
    assert len(shows) >= 20


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "ics", "google calendar"}, s.title


def test_urls_are_unique_and_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and "format=ical" not in u, u


def test_iso_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    by_url = {str(s.url): s for s in shows}
    stickin = by_url.get("https://www.etceteratheatrecamden.com/events/stickin-boy-la8zx-l263p-4z3f9-ejyzl-8g4hl")
    assert stickin is not None
    assert stickin.start_date == date(2026, 5, 10)
