from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import cast

from scout.models import ScrapeRun, ScrapeStatus, Show, ShowType, Theatre

SCHEMA = """
CREATE TABLE IF NOT EXISTS theatres (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    postcode_prefix TEXT NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theatre_slug TEXT NOT NULL REFERENCES theatres(slug),
    title TEXT NOT NULL,
    show_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    price_min INTEGER,
    price_max INTEGER,
    image_url TEXT,
    raw TEXT NOT NULL DEFAULT '{}',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shows_unique
    ON shows(theatre_slug, title, COALESCE(start_date, ''));
CREATE INDEX IF NOT EXISTS idx_shows_theatre ON shows(theatre_slug);
CREATE INDEX IF NOT EXISTS idx_shows_dates ON shows(start_date, end_date);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theatre_slug TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    shows_found INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_theatres(conn: sqlite3.Connection, theatres: list[Theatre]) -> None:
    conn.executemany(
        """
        INSERT INTO theatres (slug, name, area, postcode_prefix, category, url)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            name=excluded.name, area=excluded.area, postcode_prefix=excluded.postcode_prefix,
            category=excluded.category, url=excluded.url
        """,
        [(t.slug, t.name, t.area, t.postcode_prefix, t.category, str(t.url)) for t in theatres],
    )
    conn.commit()


def insert_show(
    conn: sqlite3.Connection,
    s: Show,
    *,
    now: datetime,
    first_seen: datetime | None = None,
) -> None:
    """Insert or update a show. `first_seen` is honored only on the initial INSERT.

    Re-inserting an existing (theatre_slug, title, start_date) updates the row but
    leaves first_seen_at alone — so an explicit `first_seen` only matters when this
    is a fresh row (e.g. after `--replace` deleted the prior row).
    """
    iso_now = now.isoformat()
    iso_first = first_seen.isoformat() if first_seen else iso_now
    conn.execute(
        """
        INSERT INTO shows (
            theatre_slug, title, show_type, description, url,
            start_date, end_date, price_min, price_max, image_url, raw,
            first_seen_at, last_seen_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(theatre_slug, title, COALESCE(start_date, '')) DO UPDATE SET
            show_type=excluded.show_type,
            description=excluded.description,
            url=excluded.url,
            end_date=excluded.end_date,
            price_min=excluded.price_min,
            price_max=excluded.price_max,
            image_url=excluded.image_url,
            raw=excluded.raw,
            last_seen_at=excluded.last_seen_at
        """,
        (
            s.theatre_slug,
            s.title,
            s.show_type,
            s.description,
            str(s.url),
            s.start_date.isoformat() if s.start_date else None,
            s.end_date.isoformat() if s.end_date else None,
            s.price_min,
            s.price_max,
            str(s.image_url) if s.image_url else None,
            json.dumps(s.raw),
            iso_first,
            iso_now,
        ),
    )
    conn.commit()


def first_seen_by_url(conn: sqlite3.Connection, slug: str) -> dict[str, str]:
    """Map of url -> first_seen_at ISO string for one theatre's existing rows."""
    rows = conn.execute(
        "SELECT url, first_seen_at FROM shows WHERE theatre_slug = ?", (slug,)
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def delete_shows_for_theatre(conn: sqlite3.Connection, slug: str) -> int:
    """Wipe all rows for `slug` from `shows`. Returns the number deleted."""
    cursor = conn.execute("DELETE FROM shows WHERE theatre_slug = ?", (slug,))
    conn.commit()
    return cursor.rowcount


def count_shows_for_theatre(conn: sqlite3.Connection, slug: str) -> int:
    """Number of rows currently stored for `slug`."""
    row = conn.execute("SELECT COUNT(*) FROM shows WHERE theatre_slug = ?", (slug,)).fetchone()
    return int(row[0]) if row else 0


def record_scrape_run(conn: sqlite3.Connection, run: ScrapeRun) -> int:
    cursor = conn.execute(
        """
        INSERT INTO scrape_runs (theatre_slug, started_at, finished_at, status, shows_found, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run.theatre_slug,
            run.started_at.isoformat(),
            run.finished_at.isoformat() if run.finished_at else None,
            run.status,
            run.shows_found,
            run.error,
        ),
    )
    conn.commit()
    return cast(int, cursor.lastrowid)


_SHOW_COLS = (
    "theatre_slug, title, show_type, description, url, "
    "start_date, end_date, price_min, price_max, image_url, raw"
)
_SHOW_COLS_S = (
    "s.theatre_slug, s.title, s.show_type, s.description, s.url, "
    "s.start_date, s.end_date, s.price_min, s.price_max, s.image_url, s.raw"
)


def _row_to_show(row: tuple) -> Show:  # type: ignore[type-arg]
    return Show(
        theatre_slug=row[0],
        title=row[1],
        show_type=cast(ShowType, row[2]),
        description=row[3],
        url=row[4],
        start_date=date.fromisoformat(row[5]) if row[5] else None,
        end_date=date.fromisoformat(row[6]) if row[6] else None,
        price_min=row[7],
        price_max=row[8],
        image_url=row[9] if row[9] else None,
        raw=json.loads(row[10]),
    )


def query_upcoming(conn: sqlite3.Connection, today: date) -> list[Show]:
    rows = conn.execute(
        f"SELECT {_SHOW_COLS} FROM shows "
        "WHERE end_date IS NULL OR end_date >= ? "
        "ORDER BY start_date IS NULL, start_date ASC",
        (today.isoformat(),),
    ).fetchall()
    return [_row_to_show(r) for r in rows]


def query_by_theatre(conn: sqlite3.Connection, slug: str) -> list[Show]:
    rows = conn.execute(
        f"SELECT {_SHOW_COLS} FROM shows WHERE theatre_slug=? ORDER BY start_date",
        (slug,),
    ).fetchall()
    return [_row_to_show(r) for r in rows]


def query_all_theatres(conn: sqlite3.Connection) -> list[Theatre]:
    rows = conn.execute(
        "SELECT slug, name, area, postcode_prefix, category, url FROM theatres ORDER BY slug"
    ).fetchall()
    return [
        Theatre(
            slug=r[0],
            name=r[1],
            area=r[2],
            postcode_prefix=r[3],
            category=cast(str, r[4]),  # type: ignore[arg-type]
            url=r[5],
        )
        for r in rows
    ]


def last_scrape_at(conn: sqlite3.Connection) -> datetime | None:
    """The most recent `finished_at` across all scrape_runs. None if never scraped."""
    row = conn.execute(
        "SELECT MAX(finished_at) FROM scrape_runs WHERE finished_at IS NOT NULL"
    ).fetchone()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def query_new_shows(conn: sqlite3.Connection) -> list[Show]:
    """Shows whose `first_seen_at` is later than their theatre's previous successful scrape.

    Returns [] for theatres with only one successful scrape on record (no baseline yet).
    """
    rows = conn.execute(
        f"""
        WITH ranked AS (
            SELECT theatre_slug, finished_at,
                   ROW_NUMBER() OVER (PARTITION BY theatre_slug ORDER BY started_at DESC) AS rn
            FROM scrape_runs
            WHERE status = 'success' AND finished_at IS NOT NULL
        ),
        prev AS (
            SELECT theatre_slug, finished_at AS prev_finished
            FROM ranked WHERE rn = 2
        )
        SELECT {_SHOW_COLS_S}
        FROM shows s
        JOIN prev ON prev.theatre_slug = s.theatre_slug
        WHERE s.first_seen_at > prev.prev_finished
        ORDER BY s.first_seen_at DESC
        """
    ).fetchall()
    return [_row_to_show(r) for r in rows]


def latest_scrape_runs(conn: sqlite3.Connection) -> list[ScrapeRun]:
    """Most recent run per theatre, ordered by slug."""
    rows = conn.execute(
        """
        SELECT theatre_slug, started_at, finished_at, status, shows_found, error
        FROM scrape_runs
        WHERE id IN (
            SELECT MAX(id) FROM scrape_runs GROUP BY theatre_slug
        )
        ORDER BY theatre_slug
        """
    ).fetchall()
    return [
        ScrapeRun(
            theatre_slug=r[0],
            started_at=datetime.fromisoformat(r[1]),
            finished_at=datetime.fromisoformat(r[2]) if r[2] else None,
            status=cast(ScrapeStatus, r[3]),
            shows_found=r[4],
            error=r[5],
        )
        for r in rows
    ]
