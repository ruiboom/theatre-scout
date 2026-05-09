from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.waterloo_east import WaterlooEastAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURE = FIXTURES / "waterloo-east.html"
DETAIL_FIXTURE = FIXTURES / "ticketsolve_show_thrillme.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return WaterlooEastAdapter().parse(
        FIXTURE.read_text(),
        "https://waterlooeast.ticketsolve.com/shows",
    )


def test_finds_at_least_one_show(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 1


def test_titles_are_real_not_navigation(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book online", "book now", "what's on", "shows", "tickets"}, (
            f"navigation text leaked as title: {s.title!r}"
        )


def test_urls_are_canonical_show_pages(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert "/ticketbooth/shows/" in str(s.url), f"non-show URL: {s.url}"


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "Thrill Me" in titles, f"Thrill Me missing; got: {titles}"


# ---- enrichment ----


def test_enrich_pulls_synopsis_from_detail_page() -> None:
    out = WaterlooEastAdapter().enrich(
        DETAIL_FIXTURE.read_text(),
        "https://waterlooeast.ticketsolve.com/ticketbooth/shows/873662331",
    )
    assert "description" in out
    desc = out["description"]
    # Generic extractor returns the first ≥60 char p (just the title + credits,
    # ~80 chars). Our longest-p heuristic should pick a real prose paragraph,
    # which is always 300+ chars on Ticketsolve detail pages.
    assert len(desc) >= 200
    # Mentions the show by name — guards against grabbing a navigation blob.
    assert "Thrill Me" in desc
