"""Coverage for the remaining May-2026 venue additions.

`arts-theatre`, `backyard-comedy-club` and `blue-elephant` are clean
GenericAdapter bulk entries with deterministic fixtures, so they get real
assertions. The five JavaScript-rendered / bot-blocked venues
(`barons-court`, `bread-and-roses`, `hope-theatre`, `space-theatre`,
`tramshed`) are intentionally best-effort: from the static fixture they may
legitimately return nothing, so we only assert that parsing never raises and
that any show it *does* return is well-formed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "slug",
    ["barons-court", "bread-and-roses", "hope-theatre", "space-theatre", "tramshed"],
)
def test_js_best_effort_never_raises_and_is_well_formed(slug: str) -> None:
    shows = _parse(slug)
    assert isinstance(shows, list)
    for s in shows:
        assert s.title and s.title.strip(), slug
        assert str(s.url).startswith(("http://", "https://")), (slug, s.url)
