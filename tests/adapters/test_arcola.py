from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.arcola import ArcolaAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "arcola.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return ArcolaAdapter().parse(
        FIXTURE.read_text(),
        "https://www.arcolatheatre.com/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real_not_button_text(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert not low.startswith("book now for"), s.title
        assert not low.startswith("find out more for"), s.title
        assert low not in {"book now", "find out more", "more info"}, s.title


def test_urls_are_canonical_event_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/event/" in u and not u.endswith("/event/"), u
        assert "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "FLUSH" in titles, f"FLUSH missing; got: {titles}"


def test_known_dates(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    flush = by_title.get("FLUSH")
    assert flush is not None
    # Listing said "6 May - 6 Jun 2026"
    assert flush.start_date == date(2026, 5, 6)
    assert flush.end_date == date(2026, 6, 6)
