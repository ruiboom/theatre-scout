from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Protocol

from scout import db
from scout.adapters.registry import all_adapters, get_adapter
from scout.enrich import extract_description, extract_image
from scout.models import ScrapeRun, Show

log = logging.getLogger(__name__)


class _ClientLike(Protocol):
    def get(self, url: str, *, stealth: bool = False) -> object | None: ...


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
    workers: int = 1,
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
        shows = _enrich_many(shows, client, workers=workers)

    # Preserve first_seen_at across --replace by URL: lets the "New shows" query
    # keep working when a bespoke adapter changes a title shape.
    prior_first_seen: dict[str, str] = {}
    if replace:
        prior_first_seen = db.first_seen_by_url(conn, slug)
        db.delete_shows_for_theatre(conn, slug)

    insert_at = now()
    for s in shows:
        prior = prior_first_seen.get(str(s.url))
        first_seen = datetime.fromisoformat(prior) if prior else None
        db.insert_show(conn, s, now=insert_at, first_seen=first_seen)

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
    workers: int = 1,
) -> list[ScrapeRun]:
    return [
        run_one(a.slug, client, conn, now=now, enrich=enrich, replace=replace, workers=workers)
        for a in all_adapters()
    ]


def _enrich_many(shows: list[Show], client: _ClientLike, *, workers: int = 1) -> list[Show]:
    """Enrich shows. With workers > 1, fetches across hosts run in parallel; the
    per-host rate limiter (in `Client`) still serializes within each host."""
    if workers <= 1 or len(shows) <= 1:
        return [_enrich(s, client) for s in shows]
    out: list[Show] = list(shows)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scout-enrich") as ex:
        for i, fut in [(i, ex.submit(_enrich, s, client)) for i, s in enumerate(shows)]:
            try:
                out[i] = fut.result()
            except Exception as exc:
                log.warning("enrich worker failed for %s: %s", shows[i].url, exc)
    return out


def _enrich(s: Show, client: _ClientLike) -> Show:
    """Fetch the show detail page and copy the description and (better) image onto the Show.

    Skips the network call if both fields are already filled from the listing page.
    """
    if s.description and s.image_url:
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
    updates: dict[str, str] = {}
    if not s.description:
        desc = extract_description(text)
        if desc:
            updates["description"] = desc
    # Detail-page images are usually canonical hero shots; prefer them over listing thumbs.
    img = extract_image(text, str(s.url))
    if img:
        updates["image_url"] = img
    if not updates:
        return s
    return s.model_copy(update=updates)


def _persist_run(conn: sqlite3.Connection, run: ScrapeRun) -> ScrapeRun:
    db.record_scrape_run(conn, run)
    return run
