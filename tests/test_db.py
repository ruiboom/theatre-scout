from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from scout import db
from scout.models import ScrapeRun, Show, Theatre

T1 = Theatre(
    slug="almeida",
    name="Almeida Theatre",
    area="Islington",
    postcode_prefix="N1",
    category="major",
    url="https://almeida.co.uk",
)
T2 = Theatre(
    slug="bush",
    name="Bush Theatre",
    area="Shepherd's Bush",
    postcode_prefix="W12",
    category="major",
    url="https://bushtheatre.co.uk",
)


def show(
    *,
    slug: str = "almeida",
    title: str = "A Doll's House",
    start: date | None = date(2026, 5, 1),
    end: date | None = date(2026, 7, 1),
    show_type: str = "play",
    url: str = "https://almeida.co.uk/shows/a-dolls-house",
) -> Show:
    return Show(
        theatre_slug=slug,
        title=title,
        show_type=show_type,
        url=url,
        start_date=start,
        end_date=end,
    )


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = db.connect(":memory:")
    db.init_schema(c)
    db.upsert_theatres(c, [T1, T2])
    return c


def test_init_schema_is_idempotent() -> None:
    c = db.connect(":memory:")
    db.init_schema(c)
    db.init_schema(c)


def test_upsert_theatres_is_idempotent(conn: sqlite3.Connection) -> None:
    db.upsert_theatres(conn, [T1, T2])
    rows = conn.execute("SELECT COUNT(*) FROM theatres").fetchone()
    assert rows[0] == 2


def test_insert_show_then_reinsert_dedupes_and_updates_last_seen(
    conn: sqlite3.Connection,
) -> None:
    t1 = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(), now=t1)
    db.insert_show(conn, show(), now=t2)

    rows = conn.execute(
        "SELECT first_seen_at, last_seen_at FROM shows WHERE theatre_slug=? AND title=?",
        ("almeida", "A Doll's House"),
    ).fetchall()
    assert len(rows) == 1
    first_seen, last_seen = rows[0]
    assert first_seen == t1.isoformat()
    assert last_seen == t2.isoformat()


def test_query_upcoming_filters_and_orders(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(title="Past", start=date(2026, 1, 1), end=date(2026, 2, 1)), now=now)
    db.insert_show(conn, show(title="Soon", start=date(2026, 6, 1), end=date(2026, 7, 1)), now=now)
    db.insert_show(conn, show(title="Later", start=date(2026, 8, 1), end=date(2026, 9, 1)), now=now)

    upcoming = db.query_upcoming(conn, today=date(2026, 5, 15))
    assert [s.title for s in upcoming] == ["Soon", "Later"]


def test_query_by_theatre_filters(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(slug="almeida", title="A"), now=now)
    db.insert_show(
        conn, show(slug="bush", title="B", url="https://bushtheatre.co.uk/shows/b"), now=now
    )
    assert [s.title for s in db.query_by_theatre(conn, "almeida")] == ["A"]
    assert [s.title for s in db.query_by_theatre(conn, "bush")] == ["B"]


def test_record_scrape_run_persists_status_and_counts(conn: sqlite3.Connection) -> None:
    run = ScrapeRun(
        theatre_slug="almeida",
        started_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 1, 10, 0, 5, tzinfo=UTC),
        status="success",
        shows_found=7,
    )
    run_id = db.record_scrape_run(conn, run)
    row = conn.execute(
        "SELECT theatre_slug, status, shows_found, error FROM scrape_runs WHERE id=?", (run_id,)
    ).fetchone()
    assert row == ("almeida", "success", 7, None)


def test_query_all_theatres_returns_typed(conn: sqlite3.Connection) -> None:
    theatres = db.query_all_theatres(conn)
    assert {t.slug for t in theatres} == {"almeida", "bush"}
    assert all(isinstance(t, Theatre) for t in theatres)


def test_insert_show_with_explicit_first_seen(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    older = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(title="Older Title"), now=now, first_seen=older)
    row = conn.execute(
        "SELECT first_seen_at, last_seen_at FROM shows WHERE title=?", ("Older Title",)
    ).fetchone()
    assert row[0] == older.isoformat()
    assert row[1] == now.isoformat()


def test_first_seen_by_url_returns_mapping(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(title="A", url="https://almeida.co.uk/a"), now=now)
    db.insert_show(conn, show(title="B", url="https://almeida.co.uk/b"), now=now)
    db.insert_show(conn, show(slug="bush", title="C", url="https://bushtheatre.co.uk/c"), now=now)
    out = db.first_seen_by_url(conn, "almeida")
    assert set(out) == {"https://almeida.co.uk/a", "https://almeida.co.uk/b"}
    assert out["https://almeida.co.uk/a"] == now.isoformat()


def test_query_new_shows_returns_only_post_previous_scrape(conn: sqlite3.Connection) -> None:
    # Two successful runs for almeida.
    run1_start = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    run1_end = datetime(2026, 5, 1, 10, 5, tzinfo=UTC)
    run2_start = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    run2_end = datetime(2026, 5, 9, 10, 5, tzinfo=UTC)
    db.record_scrape_run(
        conn,
        ScrapeRun(
            theatre_slug="almeida",
            started_at=run1_start,
            finished_at=run1_end,
            status="success",
            shows_found=1,
        ),
    )
    db.record_scrape_run(
        conn,
        ScrapeRun(
            theatre_slug="almeida",
            started_at=run2_start,
            finished_at=run2_end,
            status="success",
            shows_found=2,
        ),
    )
    db.insert_show(
        conn,
        show(title="Pre-existing", url="https://almeida.co.uk/pre"),
        now=run1_start + timedelta(seconds=1),
    )
    # New show: first_seen after run1 ended.
    db.insert_show(
        conn,
        show(title="Brand New", url="https://almeida.co.uk/new"),
        now=run2_start + timedelta(seconds=1),
    )
    new_shows = db.query_new_shows(conn)
    assert {s.title for s in new_shows} == {"Brand New"}


def test_query_new_shows_empty_when_only_one_scrape(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    db.record_scrape_run(
        conn,
        ScrapeRun(
            theatre_slug="almeida",
            started_at=now,
            finished_at=now,
            status="success",
            shows_found=1,
        ),
    )
    db.insert_show(conn, show(title="First-time Show"), now=now)
    assert db.query_new_shows(conn) == []


def test_delete_shows_for_theatre_only_removes_that_theatres_rows(
    conn: sqlite3.Connection,
) -> None:
    now = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(slug="almeida", title="A"), now=now)
    db.insert_show(
        conn, show(slug="bush", title="B", url="https://bushtheatre.co.uk/shows/b"), now=now
    )
    deleted = db.delete_shows_for_theatre(conn, "almeida")
    assert deleted == 1
    assert db.query_by_theatre(conn, "almeida") == []
    assert [s.title for s in db.query_by_theatre(conn, "bush")] == ["B"]


def test_show_with_null_start_date_round_trips(conn: sqlite3.Connection) -> None:
    now = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    db.insert_show(conn, show(title="Open Run", start=None, end=None), now=now)
    rows = db.query_by_theatre(conn, "almeida")
    assert rows[0].title == "Open Run"
    assert rows[0].start_date is None
    assert rows[0].end_date is None
