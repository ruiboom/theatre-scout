from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from scout import db
from scout.adapters.registry import all_adapters, get_adapter
from scout.enrich import extract_description
from scout.models import ScrapeRun, Show

log = logging.getLogger(__name__)


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
    enrich: bool = False,
    replace: bool = False,
) -> ScrapeRun:
    started = now()
    adapter_cls = get_adapter(slug)
    try:
        shows = adapter_cls().fetch(client)
    except Exception as exc:
        # If the fetch failed we deliberately do NOT delete existing rows —
        # better to keep stale data than wipe everything on a transient outage.
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

    if enrich:
        shows = [_enrich(s, client) for s in shows]

    if replace:
        db.delete_shows_for_theatre(conn, slug)

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
    enrich: bool = False,
    replace: bool = False,
) -> list[ScrapeRun]:
    return [
        run_one(a.slug, client, conn, now=now, enrich=enrich, replace=replace)
        for a in all_adapters()
    ]


def _enrich(s: Show, client: _ClientLike) -> Show:
    """Fetch the show detail page; if a usable description is found, copy it onto the Show."""
    if s.description:
        return s
    try:
        resp = client.get(str(s.url))
    except Exception as exc:
        log.warning("enrich: %s fetch failed: %s", s.url, exc)
        return s
    if resp is None:
        return s
    text = getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
        "utf-8", errors="replace"
    )
    desc = extract_description(text)
    if not desc:
        return s
    return s.model_copy(update={"description": desc})


def _persist_run(conn: sqlite3.Connection, run: ScrapeRun) -> ScrapeRun:
    db.record_scrape_run(conn, run)
    return run
