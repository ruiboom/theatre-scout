from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from scout import db, scraper
from scout.adapters import almeida  # noqa: F401  (registers the adapter)
from scout.models import Show
from scout.theatres import load as load_theatres

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "almeida.html"
THEATRES_YAML = Path(__file__).resolve().parent.parent / "theatres.yaml"


class FixtureClient:
    def __init__(self, fixture_html: str) -> None:
        self._html = fixture_html

    def get(self, url: str):  # type: ignore[no-untyped-def]
        class R:
            text = self._html
            content = self._html.encode()
            status_code = 200

        R._html = self._html  # type: ignore[attr-defined]
        return R()


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    c = db.connect(":memory:")
    db.init_schema(c)
    db.upsert_theatres(c, load_theatres(THEATRES_YAML))
    return c


def test_scrape_almeida_writes_shows_and_run(conn) -> None:  # type: ignore[no-untyped-def]
    client = FixtureClient(FIXTURE.read_text())
    run = scraper.run_one(
        "almeida", client, conn, now=lambda: datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    )
    assert run.status == "success"
    assert run.shows_found == 8

    shows = db.query_by_theatre(conn, "almeida")
    titles = {s.title for s in shows}
    assert "A Doll's House" in titles
    assert "Cleansed" in titles


def test_enrich_populates_descriptions_and_images(conn) -> None:  # type: ignore[no-untyped-def]
    listing_html = FIXTURE.read_text()
    detail_html = (
        "<html><head>"
        '<meta name="description" content="A bold revival of '
        "Henrik Ibsen's classic, staged with electric urgency.\">"
        '<meta property="og:image" content="https://cdn.almeida.co.uk/hero/dolls.jpg">'
        "</head><body></body></html>"
    )

    class Client:
        def get(self, url: str):  # type: ignore[no-untyped-def]
            class R:
                pass

            R.text = detail_html if "/whats-on/a-dolls-house" in url else listing_html
            R.content = R.text.encode()
            R.status_code = 200
            return R

    scraper.run_one(
        "almeida", Client(), conn, now=lambda: datetime(2026, 5, 7, tzinfo=UTC), enrich=True
    )
    rows = db.query_by_theatre(conn, "almeida")
    by_title = {r.title: r for r in rows}
    dolls = by_title["A Doll's House"]
    assert "bold revival" in dolls.description
    assert dolls.image_url == "https://cdn.almeida.co.uk/hero/dolls.jpg"


def test_replace_drops_stale_rows_before_insert(conn) -> None:  # type: ignore[no-untyped-def]
    # Pre-existing stale row that this scrape would otherwise leave behind.
    now = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    db.insert_show(
        conn,
        Show(
            theatre_slug="almeida",
            title="Stale Show With Old Bad Title",
            url="https://almeida.co.uk/whats-on/old-stale/",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 7, 1),
            show_type="play",
        ),
        now=now,
    )
    assert any(s.title.startswith("Stale") for s in db.query_by_theatre(conn, "almeida"))

    client = FixtureClient(FIXTURE.read_text())
    run = scraper.run_one("almeida", client, conn, now=lambda: now, replace=True)
    assert run.status == "success"
    titles = {s.title for s in db.query_by_theatre(conn, "almeida")}
    assert not any(t.startswith("Stale") for t in titles)
    assert "A Doll's House" in titles


def test_replace_does_not_run_if_adapter_fails(conn) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    db.insert_show(
        conn,
        Show(
            theatre_slug="almeida",
            title="Keep Me Around",
            url="https://almeida.co.uk/whats-on/keep/",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 7, 1),
            show_type="play",
        ),
        now=now,
    )

    class BoomClient:
        def get(self, url: str):  # type: ignore[no-untyped-def]
            raise RuntimeError("network down")

    run = scraper.run_one("almeida", BoomClient(), conn, now=lambda: now, replace=True)
    assert run.status == "failed"
    titles = {s.title for s in db.query_by_theatre(conn, "almeida")}
    assert "Keep Me Around" in titles  # not deleted


def test_scrape_failed_adapter_records_failure(conn) -> None:  # type: ignore[no-untyped-def]
    class BoomClient:
        def get(self, url: str):  # type: ignore[no-untyped-def]
            raise RuntimeError("network down")

    run = scraper.run_one(
        "almeida", BoomClient(), conn, now=lambda: datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    )
    assert run.status == "failed"
    assert "RuntimeError" in (run.error or "")
    assert db.query_by_theatre(conn, "almeida") == []
