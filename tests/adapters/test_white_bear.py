from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.white_bear import WhiteBearAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "white-bear.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return WhiteBearAdapter().parse(
        FIXTURE.read_text(),
        "https://www.whitebeartheatre.co.uk/whatson",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 3


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"more info", "book now", "what's on", "what’s on"}, s.title


def test_urls_are_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/whatson/" in u and not u.endswith("/whatson"), u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "Ashes and Diamonds" in titles, f"got: {titles}"


def test_images_present(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.image_url and "wixstatic" in s.image_url, s
