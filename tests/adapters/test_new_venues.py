"""Coverage for the May-2026 venue additions.

`arts-theatre`, `backyard-comedy-club` and `blue-elephant` are clean
GenericAdapter bulk entries. `barons-court`, `hope-theatre`, `tramshed` and
`bread-and-roses` are JS-rendered; their fixtures are the *stealth-rendered*
DOM (Wix / LineupNow), so they now get real assertions. Only `space-theatre`
stays best-effort — it sits behind Incapsula and is intentionally HTTP-only,
so it may legitimately return nothing.
"""

from __future__ import annotations

from pathlib import Path

from scout import adapters

adapters.load_all()

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _parse(slug: str):  # type: ignore[no-untyped-def]
    a = adapters.get_adapter(slug)()
    return a.parse((FIXTURES / f"{slug}.html").read_text(encoding="utf-8"), a.url)


def test_arts_theatre_has_shows() -> None:
    shows = _parse("arts-theatre")
    assert shows
    assert any("blippi" in s.title.lower() for s in shows), [s.title for s in shows]
    for s in shows:
        assert str(s.url).startswith("https://www.artsatmarblearch.com/"), s.url


def test_backyard_comedy_club_defaults_to_comedy() -> None:
    shows = _parse("backyard-comedy-club")
    assert shows
    # Stand-up bills rarely carry a genre keyword; the bulk comedy default
    # should still classify them as comedy.
    assert all(s.show_type == "comedy" for s in shows), [(s.title, s.show_type) for s in shows]


def test_blue_elephant_has_shows() -> None:
    shows = _parse("blue-elephant")
    assert shows
    for s in shows:
        assert s.title.strip()
        assert str(s.url).startswith("https://blueelephanttheatre.co.uk/"), s.url


def test_barons_court_lists_productions() -> None:
    shows = _parse("barons-court")
    assert len(shows) >= 5
    for s in shows:
        assert s.title.strip() and len(s.title) <= 200
        assert str(s.url).startswith("https://www.baronscourttheatre.com/"), s.url
        # Nav pages must be filtered out.
        assert (
            not str(s.url)
            .rstrip("/")
            .endswith(("/about", "/contact", "/box-office", "/upcoming-performances"))
        ), s.url
    assert len({str(s.url) for s in shows}) == len(shows), "URLs must be unique"


def test_hope_theatre_pairs_titles_with_show_pages() -> None:
    shows = _parse("hope-theatre")
    assert len(shows) >= 2
    for s in shows:
        assert s.title.strip()
        assert str(s.url).startswith("https://www.thehopetheatre.com/"), s.url
        assert not str(s.url).rstrip("/").endswith("what-s-on"), s.url


def test_tramshed_titles_default_comedy() -> None:
    shows = _parse("tramshed")
    assert len(shows) >= 3
    assert all(s.show_type == "comedy" for s in shows), [(s.title, s.show_type) for s in shows]
    assert all(str(s.url) == "https://www.tramshed.org/whatson" for s in shows)


def test_bread_and_roses_parses_lineupnow() -> None:
    shows = _parse("bread-and-roses")
    assert len(shows) >= 8
    # The widget exposes real dates — most rows should carry a start_date.
    assert sum(1 for s in shows if s.start_date is not None) >= len(shows) // 2
    for s in shows:
        assert s.title.strip() and len(s.title) <= 200
        assert str(s.url) == "https://www.breadandrosestheatre.co.uk/whats-on.html"


def test_space_theatre_best_effort_never_raises() -> None:
    # Incapsula-gated, HTTP-only by design: must not raise, may be empty.
    shows = _parse("space-theatre")
    assert isinstance(shows, list)
    for s in shows:
        assert s.title and s.title.strip()
        assert str(s.url).startswith(("http://", "https://"))
