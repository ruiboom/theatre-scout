from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.omnibus import OmnibusAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "omnibus.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return OmnibusAdapter().parse(
        FIXTURE.read_text(),
        "https://www.omnibus-clapham.org/whatson",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_dates(shows) -> None:  # type: ignore[no-untyped-def]
    import re

    date_only = re.compile(
        r"^\s*\d{1,2}(?:\s*[-|]\s*\d{1,2})?\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)",
        re.IGNORECASE,
    )
    for s in shows:
        assert not date_only.match(s.title), f"date leaked as title: {s.title!r}"
        low = s.title.strip().lower()
        assert low not in {"more info", "book now", "click to find event"}, s.title


def test_urls_are_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/whatson/" in u and not u.endswith("/whatson"), u


def test_known_shows_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "ALBATROSS" in titles, f"got: {titles}"
    assert "DUMP" in titles, f"got: {titles}"


def test_dates_parsed_for_most(shows) -> None:  # type: ignore[no-untyped-def]
    with_dates = [s for s in shows if s.start_date is not None]
    assert len(with_dates) >= len(shows) - 1
