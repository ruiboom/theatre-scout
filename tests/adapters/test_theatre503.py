from __future__ import annotations

import re
from pathlib import Path

import pytest

from scout import adapters

adapters.load_all()

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "theatre503.html"
_DATE_ONLY = re.compile(r"^[\d\s,.\-–:/]+$")


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    a = adapters.get_adapter("theatre503")()
    return a.parse(FIXTURE.read_text(encoding="utf-8"), a.url)


def test_finds_programme(shows) -> None:  # type: ignore[no-untyped-def]
    assert len(shows) >= 5


def test_titles_are_real(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title and not _DATE_ONLY.match(s.title), s.title
        assert s.title.strip().lower() not in {"more info", "book now", "book tickets"}


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    assert any(s.title.upper() == "NIUSIA" for s in shows), sorted(x.title for x in shows)


def test_urls_canonical_and_unique(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls))
    for u in urls:
        assert u.startswith("https://theatre503.com/whats-on/"), u
