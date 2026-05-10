from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.lyric_hammersmith import LyricHammersmithAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "lyric-hammersmith.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return LyricHammersmithAdapter().parse(
        FIXTURE.read_text(),
        "https://lyric.co.uk/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_more_info(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"more info", "book now", "more info."}, s.title


def test_urls_are_canonical_show_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/shows/" in u and not u.endswith("/shows/"), u
        assert "#" not in u and "/book-now" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "An Ideal Husband" in titles, f"missing; got: {titles}"


def test_known_dates_and_description(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    aih = by_title.get("An Ideal Husband")
    assert aih is not None
    assert aih.start_date == date(2026, 5, 7)
    assert aih.end_date == date(2026, 6, 6)
    assert aih.description and "Oscar Wilde" in aih.description
