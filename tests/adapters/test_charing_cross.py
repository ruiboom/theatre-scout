from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.charing_cross import CharingCrossAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "charing-cross.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return CharingCrossAdapter().parse(
        FIXTURE.read_text(),
        "https://charingcrosstheatre.co.uk/",
    )


def test_finds_at_least_one_show(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 1


def test_titles_skip_navigation_items(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"calendar view", "calendar", "show archive", "archive"}, s.title


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Dark of the Moon" in t for t in titles), f"missing; got: {titles}"


def test_urls_are_canonical_show_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/theatre/" in u and not u.endswith("/theatre/"), u
