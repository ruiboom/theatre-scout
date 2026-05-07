from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scout import db
from scout.adapters import almeida  # noqa: F401  (registers adapter for refresh test)
from scout.models import Show
from scout.theatres import load as load_theatres
from scout.web import app as web_app

THEATRES_YAML = Path(__file__).resolve().parent.parent / "theatres.yaml"


def _seed(conn: sqlite3.Connection) -> None:
    db.upsert_theatres(conn, load_theatres(THEATRES_YAML))
    now = datetime(2026, 5, 7, tzinfo=UTC)
    db.insert_show(
        conn,
        Show(
            theatre_slug="almeida",
            title="A Doll's House",
            url="https://almeida.co.uk/whats-on/a-dolls-house-play/",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 7, 1),
            show_type="play",
        ),
        now=now,
    )
    db.insert_show(
        conn,
        Show(
            theatre_slug="almeida",
            title="Past Show",
            url="https://almeida.co.uk/whats-on/past/",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            show_type="play",
        ),
        now=now,
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "web.db"
    conn = db.connect(db_path)
    db.init_schema(conn)
    _seed(conn)
    conn.close()
    web_app.app.dependency_overrides[web_app.get_db_path] = lambda: db_path
    yield TestClient(web_app.app)
    web_app.app.dependency_overrides.clear()


def test_home_lists_categories(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.text.lower()
    assert "major" in body
    assert "fringe" in body
    assert "almeida" in body


def test_theatre_page_lists_shows(client: TestClient) -> None:
    r = client.get("/theatres/almeida")
    assert r.status_code == 200
    assert "Doll" in r.text and "House" in r.text  # apostrophe gets HTML-escaped


def test_theatre_page_unknown_slug_404(client: TestClient) -> None:
    r = client.get("/theatres/does-not-exist")
    assert r.status_code == 404


def test_shows_page_lists_upcoming_only(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15"})
    assert r.status_code == 200
    assert "Doll" in r.text and "House" in r.text  # apostrophe gets HTML-escaped
    assert "Past Show" not in r.text


def test_shows_filter_by_search_query(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15", "q": "doll"})
    assert r.status_code == 200
    assert "Doll" in r.text


def test_shows_filter_by_type(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15", "type": "comedy"})
    assert r.status_code == 200
    assert "Doll" not in r.text  # the seeded show is type=play


def test_shows_filter_by_category(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15", "cat": "fringe"})
    assert r.status_code == 200
    assert "Doll" not in r.text  # almeida is major, not fringe


def test_refresh_redirects_and_calls_scraper(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: dict[str, bool] = {}

    def fake_run_all(client_, conn, **kw):  # type: ignore[no-untyped-def]
        called["yes"] = True
        return []

    monkeypatch.setattr("scout.scraper.run_all", fake_run_all)
    r = client.post("/refresh", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    assert called.get("yes") is True
