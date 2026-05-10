from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.marylebone import MaryleboneAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "marylebone.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return MaryleboneAdapter().parse(
        FIXTURE.read_text(),
        "https://www.marylebonetheatre.com/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 1


def test_titles_are_real_not_genre(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        # Generic adapter previously surfaced the genre h3 ("Theatre") as title.
        assert s.title.strip().lower() not in {"theatre", "music", "comedy"}, s.title


def test_urls_are_canonical_production_pages(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/productions/" in u and not u.endswith("/productions/"), u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Tartuffe" in t for t in titles), f"Tartuffe missing; got: {titles}"
