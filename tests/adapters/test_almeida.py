from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.almeida import AlmeidaAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "almeida.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    html = FIXTURE.read_text()
    return AlmeidaAdapter().parse(html, "https://almeida.co.uk/whats-on/")


def test_parses_eight_shows(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) == 8


def test_a_dolls_house(shows) -> None:  # type: ignore[no-untyped-def]
    s = next(s for s in shows if s.title == "A Doll's House")
    assert str(s.url) == "https://almeida.co.uk/whats-on/a-dolls-house-play/"
    assert s.start_date == date(2026, 3, 31)
    assert s.end_date == date(2026, 5, 23)
    assert str(s.image_url).startswith("https://images.almeida.co.uk/")


def test_theatre_tour_implicit_start_year(shows) -> None:  # type: ignore[no-untyped-def]
    s = next(s for s in shows if s.title == "Theatre Tour")
    assert s.start_date == date(2026, 5, 16)
    assert s.end_date == date(2026, 8, 15)


def test_short_run_same_month(shows) -> None:  # type: ignore[no-untyped-def]
    s = next(s for s in shows if s.title == "1000 (Millennia)")
    assert s.start_date == date(2026, 7, 9)
    assert s.end_date == date(2026, 7, 11)


def test_all_shows_have_required_fields(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title
        assert s.theatre_slug == "almeida"
        assert str(s.url).startswith("https://almeida.co.uk/")
