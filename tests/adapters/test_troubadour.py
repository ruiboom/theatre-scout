from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.troubadour_canary_wharf import TroubadourCanaryWharfAdapter
from scout.adapters.troubadour_wembley_park import TroubadourWembleyParkAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(scope="module")
def wembley_shows():  # type: ignore[no-untyped-def]
    return TroubadourWembleyParkAdapter().parse(
        (FIXTURES / "troubadour-wembley-park.html").read_text(),
        "https://www.troubadourtheatres.com/wembley-park-theatre",
    )


@pytest.fixture(scope="module")
def canary_shows():  # type: ignore[no-untyped-def]
    return TroubadourCanaryWharfAdapter().parse(
        (FIXTURES / "troubadour-canary-wharf.html").read_text(),
        "https://www.troubadourtheatres.com/canary-wharf-theatre",
    )


def test_wembley_finds_listed_shows(wembley_shows) -> None:  # type: ignore[no-untyped-def]
    assert len(wembley_shows) >= 1


def test_canary_finds_at_least_one_show(canary_shows) -> None:  # type: ignore[no-untyped-def]
    assert len(canary_shows) >= 1


def test_wembley_titles_are_real(wembley_shows) -> None:  # type: ignore[no-untyped-def]
    for s in wembley_shows:
        assert s.title.strip().lower() not in {"book now", "more info"}, s.title


def test_wembley_canonical_urls(wembley_shows) -> None:  # type: ignore[no-untyped-def]
    for s in wembley_shows:
        assert "/whats-on/" in str(s.url) and "troubadourtheatres.com" in str(s.url), s.url


def test_canary_known_show_present(canary_shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in canary_shows}
    assert any("Hunger Games" in t for t in titles), f"got: {titles}"


def test_wembley_known_show_present(wembley_shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in wembley_shows}
    # Fixture had "I'm Every Woman", "Dinosaur World Live" etc.
    assert any("Chaka Khan" in t or "Dinosaur" in t or "Hunger" in t for t in titles), (
        f"got: {titles}"
    )
