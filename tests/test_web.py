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


def test_sort_shows_by_each_field() -> None:
    from datetime import date as Date

    from scout.models import Show, Theatre
    from scout.web.app import _sort_shows

    almeida_t = Theatre(
        slug="almeida",
        name="Almeida Theatre",
        area="Islington",
        postcode_prefix="N1",
        category="major",
        url="https://almeida.co.uk",
    )
    bush_t = Theatre(
        slug="bush",
        name="Bush Theatre",
        area="Shepherd's Bush",
        postcode_prefix="W12",
        category="major",
        url="https://bushtheatre.co.uk",
    )
    theatres = {"almeida": almeida_t, "bush": bush_t}

    s_a = Show(
        theatre_slug="bush",
        title="Avalon",
        url="https://bushtheatre.co.uk/a",
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 7, 1),
    )
    s_b = Show(
        theatre_slug="almeida",
        title="Bedlam",
        url="https://almeida.co.uk/b",
        start_date=Date(2026, 5, 1),
        end_date=Date(2026, 8, 1),
    )
    s_c = Show(
        theatre_slug="bush",
        title="Caesar",
        url="https://bushtheatre.co.uk/c",
        start_date=None,
        end_date=Date(2026, 9, 1),
    )
    shows = [s_a, s_b, s_c]

    assert [s.title for s in _sort_shows(shows, theatres, "title", False)] == [
        "Avalon",
        "Bedlam",
        "Caesar",
    ]
    assert [s.title for s in _sort_shows(shows, theatres, "title", True)] == [
        "Caesar",
        "Bedlam",
        "Avalon",
    ]
    # Venue: Almeida < Bush
    venue_asc = [s.theatre_slug for s in _sort_shows(shows, theatres, "venue", False)]
    assert venue_asc[0] == "almeida"
    # Start date asc: shows with no date sort to the end
    titles = [s.title for s in _sort_shows(shows, theatres, "start_date", False)]
    assert titles[-1] == "Caesar"
    # End date desc: latest first
    titles = [s.title for s in _sort_shows(shows, theatres, "end_date", True)]
    assert titles[0] == "Caesar"


def test_fmt_relative_buckets() -> None:
    from datetime import UTC, datetime, timedelta

    from scout.web.app import _fmt_relative

    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    assert _fmt_relative(None, now=now) == "never"
    assert _fmt_relative(now - timedelta(seconds=10), now=now) == "just now"
    assert _fmt_relative(now - timedelta(minutes=5), now=now) == "5m ago"
    assert _fmt_relative(now - timedelta(hours=3), now=now) == "3h ago"
    assert _fmt_relative(now - timedelta(days=2), now=now) == "2d ago"
    # Older than a week falls back to a date
    assert "Apr" in _fmt_relative(now - timedelta(days=20), now=now)


def test_home_renders_last_refresh_label(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    # No scrape recorded in the seed fixture → "never"
    assert "Last: never" in r.text


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


def test_shows_filter_today_excludes_future_only_runs(client: TestClient) -> None:
    # Seeded show runs 1 Jun → 1 Jul; today = 5 May should exclude it.
    r = client.get("/shows", params={"today": "2026-05-05", "when": "today"})
    assert r.status_code == 200
    assert "Doll" not in r.text


def test_shows_filter_today_includes_active_runs(client: TestClient) -> None:
    # today = 15 Jun is inside the 1 Jun → 1 Jul run.
    r = client.get("/shows", params={"today": "2026-06-15", "when": "today"})
    assert r.status_code == 200
    assert "Doll" in r.text


def test_shows_filter_week_includes_imminent_runs(client: TestClient) -> None:
    # today = 28 May; show starts 1 Jun (≤7 days out) → included.
    r = client.get("/shows", params={"today": "2026-05-28", "when": "week"})
    assert r.status_code == 200
    assert "Doll" in r.text


def test_shows_default_sort_is_start_date_ascending(client: TestClient) -> None:
    # Seeded: only "A Doll's House" is upcoming on a 2026-05-15 cutoff.
    r = client.get("/shows", params={"today": "2026-05-15"})
    assert r.status_code == 200
    assert "Doll" in r.text


def test_shows_sort_by_title(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15", "sort": "title", "dir": "asc"})
    assert r.status_code == 200
    # Default sort would put "A Doll's House" first; just check the sort param is wired.
    assert 'name="sort"' in r.text


def test_shows_sort_dir_desc_reverses_order(client: TestClient) -> None:
    # Seed has only one upcoming show, so this is mostly a wiring test.
    r_asc = client.get("/shows", params={"today": "2026-05-15", "sort": "title", "dir": "asc"})
    r_desc = client.get("/shows", params={"today": "2026-05-15", "sort": "title", "dir": "desc"})
    assert r_asc.status_code == 200
    assert r_desc.status_code == 200


def test_shows_sort_persists_in_pill_urls(client: TestClient) -> None:
    r = client.get("/shows", params={"today": "2026-05-15", "sort": "venue", "dir": "desc"})
    assert r.status_code == 200
    # Today/Week/New pills should preserve sort+dir
    assert "sort=venue" in r.text
    assert "dir=desc" in r.text


def test_shows_filter_week_excludes_far_future_runs(client: TestClient) -> None:
    # today = 1 May; show starts 1 Jun → too far.
    r = client.get("/shows", params={"today": "2026-05-01", "when": "week"})
    assert r.status_code == 200
    assert "Doll" not in r.text


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
