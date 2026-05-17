from __future__ import annotations

import re
from pathlib import Path

import pytest

from scout import adapters

adapters.load_all()

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "battersea-arts-centre.html"
_DATE_ONLY = re.compile(r"^[\d\s,.\-–:/]+$")


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    a = adapters.get_adapter("battersea-arts-centre")()
    return a.parse(FIXTURE.read_text(encoding="utf-8"), a.url)


def test_finds_programme(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_title_is_not_the_date(shows) -> None:  # type: ignore[no-untyped-def]
    # Regression: the generic h1/h2/h3 selector picked the run-date heading;
    # this adapter must read .c-event-card__title instead.
    for s in shows:
        assert s.title and not _DATE_ONLY.match(s.title), s.title


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    titles = {s.title.lower() for s in shows}
    assert "famehungry" in titles, sorted(s.title for s in shows)


def test_urls_under_bac(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert str(s.url).startswith("https://bac.org.uk/whats-on/"), s.url
