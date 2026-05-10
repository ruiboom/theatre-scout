from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.churchill import ChurchillAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "churchill.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return ChurchillAdapter().parse(
        FIXTURE.read_text(),
        "https://trafalgartickets.com/churchill-theatre-bromley/en-GB",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_just_added(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"just added", "on sale soon", "book now", "tickets"}, s.title


def test_urls_are_unique_and_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/event/" in u and "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Midsomer" in t for t in titles), f"Midsomer Murders missing; got: {titles}"
