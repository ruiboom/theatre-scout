from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.vaults import VaultsAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "vaults.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return VaultsAdapter().parse(
        FIXTURE.read_text(),
        "https://line-up-the-vaults.pages.dev/event/52023/info",
    )


def test_finds_the_single_event(shows) -> None:  # type: ignore[no-untyped-def]
    # Currently the venue runs one show at a time and the pages.dev base URL
    # redirects to that show's detail page. If they ever publish a true listing
    # we'll see this fail and revisit.
    assert len(shows) == 1


def test_title_is_real_not_button_text(shows) -> None:  # type: ignore[no-untyped-def]
    s = shows[0]
    assert s.title.lower() not in {"tickets", "book now", "book online", "book tickets"}
    assert s.title == "Ancient Grease"


def test_url_points_to_event_page(shows) -> None:  # type: ignore[no-untyped-def]
    assert "/event/" in str(shows[0].url)


def test_image_skips_base64_placeholder(shows) -> None:  # type: ignore[no-untyped-def]
    img = shows[0].image_url
    assert img is not None
    assert not img.startswith("data:")
    assert "imgix" in img or img.startswith("http")


def test_dates_extracted_from_calendar(shows) -> None:  # type: ignore[no-untyped-def]
    s = shows[0]
    # Fixture calendar shows performances on 12-16 May and 19-22 May 2026.
    assert s.start_date == date(2026, 5, 12)
    assert s.end_date == date(2026, 5, 22)


def test_description_is_substantive(shows) -> None:  # type: ignore[no-untyped-def]
    desc = shows[0].description
    assert desc and len(desc) >= 60
    assert desc.lower() != "ancient grease"
