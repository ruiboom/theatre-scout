from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.upstairs_at_the_gatehouse import UpstairsAtTheGatehouseAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURE = FIXTURES / "upstairs-at-the-gatehouse.html"
DETAIL_FIXTURE = FIXTURES / "ticketsolve_show_marilyn.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return UpstairsAtTheGatehouseAdapter().parse(
        FIXTURE.read_text(),
        "https://upstairsatthegatehouse.ticketsolve.com/shows",
    )


def test_finds_a_handful_of_shows(shows) -> None:  # type: ignore[no-untyped-def]
    # Fixture had 10 cards at capture time; allow drift but rule out the old
    # bug where the adapter returned a single "What's On" navigation item.
    assert len(shows) >= 5


def test_titles_are_real_not_navigation(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"what's on", "what’s on", "shows", "tickets", "book online"}, (
            f"navigation text leaked as title: {s.title!r}"
        )


def test_urls_are_canonical_show_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls)), "duplicate URLs"
    for u in urls:
        assert "/ticketbooth/shows/" in u, f"non-show URL: {u}"


def test_images_are_extracted_when_present(shows) -> None:  # type: ignore[no-untyped-def]
    # Some Ticketsolve cards intentionally render a CSS gradient instead of a
    # poster (no image uploaded yet); we just want to prove the extractor works
    # for the shows that do have one, and that what we pull is a real URL.
    with_img = [s for s in shows if s.image_url]
    assert len(with_img) >= 1
    for s in with_img:
        assert str(s.image_url).startswith("http"), s.image_url


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert "Marilyn" in titles, f"Marilyn missing; got: {titles}"


# ---- enrichment ----


def test_enrich_pulls_synopsis_from_detail_page() -> None:
    out = UpstairsAtTheGatehouseAdapter().enrich(
        DETAIL_FIXTURE.read_text(),
        "https://upstairsatthegatehouse.ticketsolve.com/ticketbooth/shows/1173671950",
    )
    assert "description" in out
    desc = out["description"]
    assert len(desc) >= 100
    # Generic extractor would pick the first ≥60 char p (subtitle); ours picks
    # the longest paragraph, which on this page is the actual synopsis.
    assert "Marilyn" in desc or "centenary" in desc.lower()
