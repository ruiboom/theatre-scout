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
    """Single-theatre pipeline: listing → optional enrich → DB.

    `workers` only matters when this theatre has shows on multiple hosts; same-host
    shows are still serialized by the per-host rate limiter.
    """
    started = now()
    adapter_cls = get_adapter(slug)
    try:
        shows = adapter_cls().fetch(client)
    except Exception as exc:
        return _persist_run(
            conn, _failed_run(slug, started, now(), f"{type(exc).__name__}: {exc}")
        )

    if enrich:
        shows = _enrich_many(shows, client, workers=workers)

    _write_shows(conn, slug, shows, when=now(), replace=replace)
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
    """Three-phase pipeline so that the slowest step (per-show enrichment) can
    fan out across hosts globally — not just within one theatre.

    Phase 1: serial listing scrape per adapter.
    Phase 2: parallel enrichment across every show from every theatre.
    Phase 3: serial DB writes per theatre.
    """
    fetched: list[tuple[str, list[Show], datetime]] = []  # slug → (shows, started_at)
    failed_runs: list[ScrapeRun] = []

    # ---- Phase 1: listings (serial; stealth path uses single shared browser) ----
    for adapter_cls in all_adapters():
        slug = adapter_cls.slug
        started = now()
        try:
            shows = adapter_cls().fetch(client)
        except Exception as exc:
            failed_runs.append(_failed_run(slug, started, now(), f"{type(exc).__name__}: {exc}"))
            continue
        fetched.append((slug, shows, started))

    # ---- Phase 2: enrichment (parallel across all shows) ----
    if enrich:
        flat = [s for _, shows, _ in fetched for s in shows]
        enriched = _enrich_many(flat, client, workers=workers)
        # Re-split back per theatre, preserving order.
        idx = 0
        re_grouped: list[tuple[str, list[Show], datetime]] = []
        for slug, shows, started in fetched:
            n = len(shows)
            re_grouped.append((slug, list(enriched[idx : idx + n]), started))
            idx += n
        fetched = re_grouped

    # ---- Phase 3: DB writes (serial) ----
    runs: list[ScrapeRun] = []
    for slug, shows, started in fetched:
        _write_shows(conn, slug, shows, when=now(), replace=replace)
        runs.append(
            _persist_run(
                conn,
                ScrapeRun(
                    theatre_slug=slug,
                    started_at=started,
                    finished_at=now(),
                    status="success",
                    shows_found=len(shows),
                ),
            )
        )
    for r in failed_runs:
        runs.append(_persist_run(conn, r))
    runs.sort(key=lambda r: r.theatre_slug)
    return runs


def _write_shows(
    conn: sqlite3.Connection,
    slug: str,
    shows: list[Show],
    *,
    when: datetime,
    replace: bool,
) -> None:
    """Insert (and optionally replace) shows for a single theatre.

    Preserves first_seen_at across --replace by URL: lets the "New shows" query
    keep working when a bespoke adapter changes a title shape.
    """
    prior_first_seen: dict[str, str] = {}
    if replace:
        prior_first_seen = db.first_seen_by_url(conn, slug)
        db.delete_shows_for_theatre(conn, slug)
    for s in shows:
        prior = prior_first_seen.get(str(s.url))
        first_seen = datetime.fromisoformat(prior) if prior else None
        db.insert_show(conn, s, now=when, first_seen=first_seen)


def _failed_run(slug: str, started: datetime, finished: datetime, error: str) -> ScrapeRun:
    return ScrapeRun(
        theatre_slug=slug,
        started_at=started,
        finished_at=finished,
        status="failed",
        error=error,
    )


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
    img = extract_image(text, str(s.url))
    if img:
        updates["image_url"] = img
    if not updates:
        return s
    return s.model_copy(update=updates)


def _persist_run(conn: sqlite3.Connection, run: ScrapeRun) -> ScrapeRun:
    db.record_scrape_run(conn, run)
    return run
