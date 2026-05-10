from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.yard import YardAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "yard.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return YardAdapter().parse(
        FIXTURE.read_text(),
        "https://www.theyardtheatre.co.uk/whats-on",
    )


def test_finds_at_least_one_show(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 1


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "tickets", "what's on"}, s.title


def test_urls_are_event_pages_no_tickets(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and "/tickets/" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "Philosophy of the World" in titles, f"missing; got: {titles}"


def test_known_dates(shows) -> None:  # type: ignore[no-untyped-def]
    s = next(x for x in shows if x.title == "Philosophy of the World")
    assert s.start_date == date(2026, 7, 14)
    assert s.end_date == date(2026, 7, 25)


def test_image_extracted(shows) -> None:  # type: ignore[no-untyped-def]
    s = next(x for x in shows if x.title == "Philosophy of the World")
    # Yard wraps images in /_next/image?url=<encoded>; the adapter unwraps so
    # the stored URL points directly at the underlying Sanity CDN asset.
    assert s.image_url is not None
    assert "cdn.sanity.io" in s.image_url, s.image_url
