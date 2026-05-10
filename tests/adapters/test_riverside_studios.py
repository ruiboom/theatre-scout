from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.riverside_studios import RiversideStudiosAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "riverside-studios.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return RiversideStudiosAdapter().parse(
        FIXTURE.read_text(),
        "https://riversidestudios.co.uk/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_more_info(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title.strip().lower() not in {"more info", "book now", "tickets"}, s.title


def test_urls_are_canonical_event_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/whats-on/" in u and not u.endswith("/whats-on/"), u
