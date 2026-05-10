from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.old_vic import OldVicAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "old-vic.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return OldVicAdapter().parse(
        FIXTURE.read_text(),
        "https://www.oldvictheatre.com/productions/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 1


def test_titles_are_real_not_page_header(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title.strip().lower() != "productions", s.title


def test_urls_are_canonical_show_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        # Old Vic uses /stage/<slug>/ for production detail pages.
        assert "/stage/" in u or "/productions/" in u, u
        assert "#" not in u, u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Cuckoo" in t for t in titles), f"Cuckoo's Nest missing; got: {titles}"
