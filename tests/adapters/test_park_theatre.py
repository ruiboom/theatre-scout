from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.park_theatre import ParkTheatreAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "park-theatre.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return ParkTheatreAdapter().parse(FIXTURE.read_text(), "https://parktheatre.co.uk/whats-on/")


def test_returns_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) > 0


def test_no_find_out_more_prefixes_in_titles(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert "Find out more about" not in s.title, f"unclean title: {s.title!r}"


def test_no_book_now_titles(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title.lower() != "book now"


def test_no_event_instances_fragment_in_urls(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert "#event-instances" not in str(s.url)


def test_dedup_by_canonical_url(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))


def test_known_show_title_is_clean(shows) -> None:  # type: ignore[no-untyped-def]
    catherine = next((s for s in shows if "Catherine Bohart" in s.title), None)
    assert catherine is not None
    assert catherine.title.startswith("Catherine Bohart")


def test_titles_have_no_leading_newlines_or_double_spaces(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title == s.title.strip()
        assert "\n" not in s.title
        assert "  " not in s.title
