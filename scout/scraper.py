from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from scout import db
from scout.adapters.registry import all_adapters, get_adapter
from scout.models import ScrapeRun


class _ClientLike(Protocol):
    def get(self, url: str) -> object | None: ...


def _utcnow() -> datetime:
    return datetime.now(UTC)


def run_one(
    slug: str,
    client: _ClientLike,
    conn: sqlite3.Connection,
    *,
    now: Callable[[], datetime] = _utcnow,
) -> ScrapeRun:
    started = now()
    adapter_cls = get_adapter(slug)
    try:
        shows = adapter_cls().fetch(client)
    except Exception as exc:
        return _persist_run(
            conn,
            ScrapeRun(
                theatre_slug=slug,
                started_at=started,
                finished_at=now(),
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
            ),
        )

    insert_at = now()
    for s in shows:
        db.insert_show(conn, s, now=insert_at)

    return _persist_run(
        conn,
        ScrapeRun(
            theatre_slug=slug,
            started_at=started,
            finished_at=now(),
            status="success",
            shows_found=len(shows),
        ),
    )


def run_all(
    client: _ClientLike,
    conn: sqlite3.Connection,
    *,
    now: Callable[[], datetime] = _utcnow,
) -> list[ScrapeRun]:
    return [run_one(a.slug, client, conn, now=now) for a in all_adapters()]


def _persist_run(conn: sqlite3.Connection, run: ScrapeRun) -> ScrapeRun:
    db.record_scrape_run(conn, run)
    return run
