from __future__ import annotations

from pathlib import Path

import pytest

from scout import adapters

adapters.load_all()

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "courtyard.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    a = adapters.get_adapter("courtyard")()
    return a.parse(FIXTURE.read_text(encoding="utf-8"), a.url)


def test_finds_programme(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_deslugged_from_url(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    # billy-liar -> "Billy Liar", way-upstream -> "Way Upstream"
    assert "Billy Liar" in titles, sorted(titles)
    assert "Way Upstream" in titles, sorted(titles)


def test_seetickets_links_and_deduped(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert "seetickets.com/event/" in str(s.url), s.url
    # way-upstream appears under several performance ids in the fixture.
    assert sum(1 for s in shows if s.title == "Way Upstream") == 1
