from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.tower import TowerAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "tower.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return TowerAdapter().parse(
        FIXTURE.read_text(),
        "https://www.towertheatre.org.uk/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "tickets"}, s.title


def test_urls_are_unique_and_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert u.startswith("http") and "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Clyde" in t or "Ink" in t for t in titles), f"got: {titles}"
