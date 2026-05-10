from __future__ import annotations

from pathlib import Path

import pytest

from scout.adapters.old_red_lion import OldRedLionAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "old-red-lion.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return OldRedLionAdapter().parse(
        FIXTURE.read_text(),
        "https://weareoldred.co.uk/whats-on/",
    )


def test_finds_listed_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        low = s.title.strip().lower()
        assert low not in {"book now", "more info", "tickets", "what's on", "what’s on"}, s.title


def test_urls_are_unique_and_canonical(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert "/whats-on/" in u and not u.endswith("/whats-on/"), u


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title for s in shows}
    assert any("Walking Each Other Home" in t for t in titles), f"got: {titles}"
