from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.eventim_apollo import EventimApolloAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "eventim-apollo.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return EventimApolloAdapter().parse(
        FIXTURE.read_text(),
        "https://www.eventimapollo.com/events/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    # Generic adapter only ever returned 1 row titled "Information". Real
    # listing has many.
    assert len(shows) >= 10


def test_titles_are_real_not_information(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"information", "buy tickets", "on sale soon"}, s.title


def test_urls_are_unique_and_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and not u.endswith("/events/"), u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Jujutsu Kaisen" in t for t in titles), f"got: {titles}"
