from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.pleasance import PleasanceAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "pleasance.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return PleasanceAdapter().parse(FIXTURE.read_text(), "https://www.pleasance.co.uk/events")


def test_filters_to_london_only(shows) -> None:  # type: ignore[no-untyped-def]
    # Pleasance lists ~250 Edinburgh Fringe shows alongside the London Islington
    # programme. Edinburgh shows must not appear here.
    assert 30 <= len(shows) <= 150, f"expected 30–150 London shows, got {len(shows)}"


def test_titles_stripped_of_book_tickets_prefix(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert not s.title.lower().startswith("book tickets for"), f"unclean title: {s.title!r}"


def test_no_book_now_titles(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title.lower() not in {"book now", "book tickets"}


def test_urls_canonical_and_unique(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls)), "URLs should be deduped"
    for u in urls:
        assert "#" not in u, f"fragment leaked: {u}"


def test_known_london_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Down To Chance" in t for t in titles), titles
