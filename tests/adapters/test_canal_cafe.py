from __future__ import annotations

from pathlib import Path

import pytest

from scout import adapters

adapters.load_all()

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "canal-cafe.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    a = adapters.get_adapter("canal-cafe")()
    return a.parse(FIXTURE.read_text(encoding="utf-8"), a.url)


def test_finds_programme(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_newsrevue_present_and_comedy(shows) -> None:  # type: ignore[no-untyped-def]
    nr = [s for s in shows if s.title.lower() == "newsrevue"]
    assert nr, sorted(s.title for s in shows)
    # No genre keyword in the title -> classifier is silent -> comedy default.
    assert nr[0].show_type == "comedy", nr[0]


def test_no_per_show_page_uses_listings_url(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert str(s.url) == "https://canalcafetheatre.com/our-shows/", s.url


def test_titles_unique_and_nonempty(shows) -> None:  # type: ignore[no-untyped-def]
    titles = [s.title for s in shows]
    assert all(t.strip() for t in titles)
    assert len(titles) == len({t.lower() for t in titles})
