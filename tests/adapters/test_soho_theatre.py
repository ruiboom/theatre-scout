from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.soho_theatre import SohoTheatreAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
PAGE1 = FIXTURES / "soho-theatre.html"
PAGE2 = FIXTURES / "soho-theatre-page2.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return SohoTheatreAdapter().parse(
        PAGE1.read_text(),
        "https://sohotheatre.com/dean-street/",
    )


def test_finds_first_page_shows(shows) -> None:  # type: ignore[no-untyped-def]
    # Captured fixture had 17 cards; allow drift but rule out the old bug
    # where a single anchor produced the title "Soho Tender By Dave Harris ...".
    assert 10 <= len(shows) <= 30


def test_titles_are_just_the_title(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        # Generic adapter used to grab the venue badge + subtitle + dates as
        # part of the title.
        assert not s.title.startswith("Soho "), s.title
        assert "May 26" not in s.title, s.title
        assert "Directed by" not in s.title, s.title


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    by_title = {s.title: s for s in shows}
    tender = by_title.get("Tender")
    assert tender is not None, f"Tender missing; got titles: {sorted(by_title)}"
    # Listing said "Sat 9 May – Sat 6 Jun 26" → 2026.
    assert tender.start_date == date(2026, 5, 9)
    assert tender.end_date == date(2026, 6, 6)
    assert tender.description and "Dave Harris" in tender.description
    assert tender.price_min == 1500  # "From £15"
    assert (
        tender.image_url
        and "sohotheatre.com" in tender.image_url
        or "exactdn" in (tender.image_url or "")
    )


def test_urls_canonical_and_unique(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/events/" in u and "#" not in u, u


def test_pagination_walks_pages_via_fetch() -> None:
    """fetch() should keep loading until no `a.pagination-button` remains."""
    page_calls: list[str] = []
    page_responses = {
        "https://sohotheatre.com/dean-street/": PAGE1.read_text(),
        "https://sohotheatre.com/dean-street/page/2/": PAGE2.read_text(),
    }

    class _FakeResp:
        def __init__(self, text: str):
            self.text = text

    class _FakeClient:
        def get(self, url: str, *, stealth: bool = False) -> object | None:  # noqa: ARG002
            page_calls.append(url)
            text = page_responses.get(url)
            return _FakeResp(text) if text is not None else None

    shows = SohoTheatreAdapter().fetch(_FakeClient())
    # Both pages should have been requested in order.
    assert page_calls[0] == "https://sohotheatre.com/dean-street/"
    assert page_calls[1] == "https://sohotheatre.com/dean-street/page/2/"
    # Combined unique URLs from both fixtures, deduped.
    assert len(shows) > 25
