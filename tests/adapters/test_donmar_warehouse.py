from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.donmar_warehouse import DonmarWarehouseAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "donmar-warehouse.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return DonmarWarehouseAdapter().parse(
        FIXTURE.read_text(),
        "https://www.donmarwarehouse.com/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    # Fixture has 8 events at capture time; allow drift but rule out the old
    # bug where every "Book now" / "More info" anchor became a row.
    assert 3 <= len(shows) <= 20


def test_titles_are_real_not_button_text(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "book online", "tickets"}, s.title


def test_urls_are_canonical_event_pages_no_fragment(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls)), "duplicate URLs"
    for u in urls:
        assert "/events/" in u, u
        assert "#" not in u, f"fragment leaked: {u}"


def test_all_have_images(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.image_url is not None and "donmar" in str(s.image_url).lower(), s


def test_all_have_descriptions(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.description, f"empty description for {s.title!r}"


def test_iso_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    mass = by_title.get("Mass")
    assert mass is not None
    # Listing exposes startDate=2026-05-11, endDate=2026-06-06.
    assert mass.start_date == date(2026, 5, 11)
    assert mass.end_date == date(2026, 6, 6)
