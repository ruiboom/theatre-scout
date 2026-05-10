from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.new_wimbledon import NewWimbledonAdapter
from scout.adapters.richmond import RichmondAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(scope="module")
def wimbledon():  # type: ignore[no-untyped-def]
    return NewWimbledonAdapter().parse(
        (FIXTURES / "new-wimbledon.html").read_text(),
        "https://www.atgtickets.com/venues/new-wimbledon-theatre/whats-on/",
    )


@pytest.fixture(scope="module")
def richmond():  # type: ignore[no-untyped-def]
    return RichmondAdapter().parse(
        (FIXTURES / "richmond.html").read_text(),
        "https://www.atgtickets.com/venues/richmond-theatre/whats-on/",
    )


def test_wimbledon_finds_listed_shows(wimbledon) -> None:  # type: ignore[no-untyped-def]
    assert len(wimbledon) >= 5


def test_richmond_finds_listed_shows(richmond) -> None:  # type: ignore[no-untyped-def]
    assert len(richmond) >= 5


def test_titles_are_real_not_buy_tickets(wimbledon, richmond) -> None:  # type: ignore[no-untyped-def]
    for s in [*wimbledon, *richmond]:
        low = s.title.strip().lower()
        assert not low.startswith("buy tickets"), s.title
        assert not low.startswith("more information"), s.title


def test_urls_are_canonical_show_pages(wimbledon, richmond) -> None:  # type: ignore[no-untyped-def]
    for s in [*wimbledon, *richmond]:
        u = str(s.url)
        assert "/shows/" in u, u
        assert "/calendar/" not in u, u


def test_wimbledon_known_show(wimbledon) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in wimbledon}
    assert "Annie" in titles, f"got: {titles}"


def test_richmond_known_show(richmond) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in richmond}
    assert "Allegra" in titles, f"got: {titles}"
