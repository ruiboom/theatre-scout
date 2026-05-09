from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.bloomsbury import BloomsburyAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "bloomsbury.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return BloomsburyAdapter().parse(
        FIXTURE.read_text(),
        "https://www.bloomsburytheatre.com/events",
    )


def test_finds_all_cards_in_fixture(shows) -> None:  # type: ignore[no-untyped-def]
    # Captured fixture had 10 event cards.
    assert len(shows) == 10


def test_titles_are_real_not_navigation(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"events", "what's on", "what’s on"}, s.title


def test_urls_are_canonical_event_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/event/" in u and u.startswith("https://"), u


def test_all_have_images(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.image_url is not None and str(s.image_url).startswith("http"), s


def test_all_have_descriptions(shows) -> None:  # type: ignore[no-untyped-def]
    # Every Bloomsbury card has a synopsis paragraph in `.es-desc`.
    for s in shows:
        assert s.description, f"empty description for {s.title!r}"


def test_uk_dates_parsed_correctly(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    eddie = by_title.get("Let Me Land | Eddie Kadi")
    assert eddie is not None
    # Listing said "08/05/2026 19:30" — UK dd/mm/yyyy.
    assert eddie.start_date == date(2026, 5, 8)
    assert eddie.end_date == date(2026, 5, 8)


def test_date_range_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    # "Platform 1" was listed as "22/05/2026 - 23/05/2026"
    by_title = {s.title: s for s in shows}
    p1 = by_title.get("Platform 1")
    assert p1 is not None
    assert p1.start_date == date(2026, 5, 22)
    assert p1.end_date == date(2026, 5, 23)


def test_comedy_tag_classifies_as_comedy(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    eddie = by_title.get("Let Me Land | Eddie Kadi")
    assert eddie is not None
    assert eddie.show_type == "comedy"
