"""A transient empty scrape must not wipe a venue under --replace.

Regression guard for the data-loss path: an adapter that momentarily returns 0
shows (site blip / anti-bot during a run) used to DELETE the venue's rows and
insert nothing, blanking it until the next good scrape. `_write_shows` now skips
the destructive replace when there's nothing to write.

Mirror of the platform's tests/test_writer_replace_guard.py, using a real
in-memory SQLite DB.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

import pytest

from scout import db
from scout.models import Show, Theatre
from scout.scraper import _write_shows

WHEN = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)

T = Theatre(
    slug="backyard-comedy-club",
    name="Backyard Comedy Club",
    area="Bethnal Green",
    postcode_prefix="E2",
    category="fringe",
    url="https://backyardcomedyclub.co.uk",
)


def _show(title: str, url: str) -> Show:
    return Show(
        theatre_slug=T.slug,
        title=title,
        show_type="comedy",
        url=url,
        start_date=date(2026, 6, 1),
    )


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = db.connect(":memory:")
    db.init_schema(c)
    db.upsert_theatres(c, [T])
    return c


def test_replace_with_empty_shows_preserves_existing(conn: sqlite3.Connection) -> None:
    _write_shows(conn, T.slug, [_show("Lee Hurst", "https://e.com/1")], when=WHEN, replace=True)
    assert db.count_shows_for_theatre(conn, T.slug) == 1

    # A transient empty scrape under --replace.
    _write_shows(conn, T.slug, [], when=WHEN, replace=True)

    # The blip must NOT have wiped the venue.
    assert db.count_shows_for_theatre(conn, T.slug) == 1


def test_replace_with_empty_shows_on_fresh_venue_is_noop(
    conn: sqlite3.Connection,
) -> None:
    # No existing rows: still a no-op, and must not error.
    _write_shows(conn, T.slug, [], when=WHEN, replace=True)
    assert db.count_shows_for_theatre(conn, T.slug) == 0


def test_replace_with_shows_still_replaces(conn: sqlite3.Connection) -> None:
    _write_shows(conn, T.slug, [_show("Old", "https://e.com/old")], when=WHEN, replace=True)
    _write_shows(conn, T.slug, [_show("New", "https://e.com/new")], when=WHEN, replace=True)

    titles = {s.title for s in db.query_by_theatre(conn, T.slug)}
    assert titles == {"New"}  # the genuine replace still drops the stale row
