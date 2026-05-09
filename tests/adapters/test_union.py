from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scout.adapters.union import UnionAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURE = FIXTURES / "union.html"
DETAIL_WITH_SYNOPSIS = FIXTURES / "union_show_with_synopsis.html"
DETAIL_SPARSE = FIXTURES / "union_show_sparse.html"


@pytest.fixture(scope="module")
def shows():  # type: ignore[no-untyped-def]
    return UnionAdapter().parse(FIXTURE.read_text(), "https://uniontheatre.biz/whats-on/")


def test_titles_are_real_not_button_text(shows) -> None:  # type: ignore[no-untyped-def]
    for s in shows:
        assert s.title.lower() not in {"read more", "book tickets", "book now"}, (
            f"button text leaked as title: {s.title!r}"
        )


def test_urls_are_show_pages_and_unique(shows) -> None:  # type: ignore[no-untyped-def]
    urls = [str(s.url) for s in shows]
    assert len(urls) == len(set(urls)), "duplicate URLs"
    for u in urls:
        assert "/show/" in u, f"unexpected URL: {u}"


def test_dates_parsed(shows) -> None:  # type: ignore[no-untyped-def]
    # Vast majority of cards expose a parseable date or range; allow a tiny tail
    # of TBA / unusual entries.
    with_dates = [s for s in shows if s.start_date is not None]
    assert len(with_dates) / len(shows) >= 0.9, (
        f"only {len(with_dates)}/{len(shows)} shows had dates"
    )


def test_known_show_present(shows) -> None:  # type: ignore[no-untyped-def]
    by_url = {str(s.url): s for s in shows}
    flyology = by_url.get("https://uniontheatre.biz/show/flyology/")
    assert flyology is not None, "Flyology missing"
    assert flyology.title == "Flyology"
    assert flyology.start_date == date(2026, 5, 5)
    assert flyology.end_date == date(2026, 5, 8)


# ---- enrichment ----


def test_enrich_extracts_synopsis_paragraph() -> None:
    out = UnionAdapter().enrich(
        DETAIL_WITH_SYNOPSIS.read_text(),
        "https://uniontheatre.biz/show/grindr-the-opera/",
    )
    assert "description" in out
    assert "Grindr" in out["description"]
    assert len(out["description"]) >= 60


def test_enrich_extracts_prices_from_tickets_block() -> None:
    out = UnionAdapter().enrich(
        DETAIL_WITH_SYNOPSIS.read_text(),
        "https://uniontheatre.biz/show/grindr-the-opera/",
    )
    assert out.get("price_min") is not None
    assert out.get("price_max") is not None
    assert out["price_min"] >= 100  # at least £1 (in pence)


def test_enrich_skips_zero_priced_access_seats() -> None:
    # Sparse fixture has £13 (Full) and £0 (Access). min must be £13, not £0.
    out = UnionAdapter().enrich(
        DETAIL_SPARSE.read_text(),
        "https://uniontheatre.biz/show/i-dont-want-to-imagine-the-future-with-you-anymore/",
    )
    assert out.get("price_min") == 1300
    assert out.get("price_max") == 1300


def test_enrich_omits_description_when_page_has_no_synopsis() -> None:
    out = UnionAdapter().enrich(
        DETAIL_SPARSE.read_text(),
        "https://uniontheatre.biz/show/i-dont-want-to-imagine-the-future-with-you-anymore/",
    )
    # No <p> with substantive copy on this page; description must not appear.
    assert "description" not in out
