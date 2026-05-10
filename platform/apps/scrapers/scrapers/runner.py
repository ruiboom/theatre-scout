"""3-phase orchestrator. Mirrors scout/scraper.py.

Phase 1 — listings, serial. Stealth fetches share one browser thread, so
parallelising here would mean N browsers up at once.

Phase 2 — enrichment, parallel. Every show from every venue is fanned across
distinct hosts (round-robin) so a single dominant venue with 300 shows can't
absorb every worker and stall behind its own per-host rate limit.

Phase 3 — DB writes, serial. Postgres handles concurrency fine but we want a
deterministic ordering for the per-venue ScrapeRun records.

A single adapter raising never crashes the run; failures are recorded as a
`failed` ScrapeRun and the orchestrator moves on.
"""

from __future__ import annotations

import logging
import urllib.parse
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Protocol

from .adapters import all_adapters, get_adapter, load_all
from .models import ScrapeRun, Show
from .writer import record_run, write_shows

log = logging.getLogger(__name__)


class _ClientLike(Protocol):
    def get(self, url: str, *, stealth: bool = False) -> object | None: ...


def _utcnow() -> datetime:
    return datetime.now(UTC)


def run_one(
    slug: str,
    client: _ClientLike,
    *,
    now: Callable[[], datetime] = _utcnow,
    enrich: bool = False,
    replace: bool = False,
    workers: int = 1,
) -> ScrapeRun:
    """Single-theatre pipeline: listing → optional enrich → DB."""
    load_all()
    started = now()
    adapter_cls = get_adapter(slug)
    try:
        shows = adapter_cls().fetch(client)
    except Exception as exc:
        run = _failed_run(slug, started, now(), f"{type(exc).__name__}: {exc}")
        record_run(run)
        return run

    if enrich:
        shows = _enrich_many(shows, client, workers=workers)

    write_shows(slug, shows, replace=replace)
    run = ScrapeRun(
        theatre_slug=slug,
        started_at=started,
        finished_at=now(),
        status="success",
        shows_found=len(shows),
    )
    record_run(run)
    return run


def run_all(
    client: _ClientLike,
    *,
    now: Callable[[], datetime] = _utcnow,
    enrich: bool = False,
    replace: bool = False,
    workers: int = 1,
) -> list[ScrapeRun]:
    """Three-phase pipeline so the slowest step (per-show enrichment) can fan
    out across hosts globally — not just within one theatre."""
    load_all()
    fetched: list[tuple[str, list[Show], datetime]] = []
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
        write_shows(slug, shows, replace=replace)
        run = ScrapeRun(
            theatre_slug=slug,
            started_at=started,
            finished_at=now(),
            status="success",
            shows_found=len(shows),
        )
        record_run(run)
        runs.append(run)
    for r in failed_runs:
        record_run(r)
        runs.append(r)
    runs.sort(key=lambda r: r.theatre_slug)
    return runs


def _failed_run(slug: str, started: datetime, finished: datetime, error: str) -> ScrapeRun:
    return ScrapeRun(
        theatre_slug=slug,
        started_at=started,
        finished_at=finished,
        status="failed",
        error=error,
    )


def _enrich_many(shows: list[Show], client: _ClientLike, *, workers: int = 1) -> list[Show]:
    """Enrich shows. Workers > 1 fans across hosts; the per-host rate limiter
    inside `Client` still serialises within each host.

    Submission order is round-robin by host so the worker pool fans out across
    distinct hosts immediately — otherwise a single dominant host would absorb
    every worker and stall behind its own rate limit.
    """
    if workers <= 1 or len(shows) <= 1:
        return [_enrich(s, client) for s in shows]
    submission_order = _host_round_robin(shows)
    out: list[Show] = list(shows)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="scrapers-enrich") as ex:
        futures = [(i, ex.submit(_enrich, shows[i], client)) for i in submission_order]
        for i, fut in futures:
            try:
                out[i] = fut.result()
            except Exception as exc:
                log.warning("enrich worker failed for %s: %s", shows[i].url, exc)
    return out


def _host_round_robin(shows: list[Show]) -> list[int]:
    """Return original-index order such that adjacent items are on different hosts."""
    by_host: dict[str, list[int]] = {}
    for i, s in enumerate(shows):
        host = urllib.parse.urlparse(str(s.url)).netloc
        by_host.setdefault(host, []).append(i)
    out: list[int] = []
    queues = [iter(idxs) for idxs in by_host.values()]
    while queues:
        next_queues = []
        for q in queues:
            try:
                out.append(next(q))
                next_queues.append(q)
            except StopIteration:
                continue
        queues = next_queues
    return out


def _enrich(s: Show, client: _ClientLike) -> Show:
    """Fetch the show detail page and merge adapter-extracted fields onto the Show.

    Merge policy (matches scout/scraper.py::_enrich):
      - description: only set if empty (listing copy wins when present).
      - image_url: always overwrite (detail-page hero usually beats listing thumb).
      - price_min / price_max: only set if currently None.
    """
    if s.description and s.image_url and s.price_min is not None:
        return s
    try:
        adapter_cls = get_adapter(s.theatre_slug)
    except KeyError:
        return s
    try:
        resp = client.get(str(s.url), stealth=adapter_cls.requires_js)
    except Exception as exc:
        log.warning("enrich: %s fetch failed: %s", s.url, exc)
        return s
    if resp is None:
        return s
    text = getattr(resp, "text", None) or getattr(resp, "content", b"").decode(
        "utf-8", errors="replace"
    )
    try:
        candidates = adapter_cls().enrich(text, str(s.url))
    except Exception as exc:
        log.warning("enrich: %s parse failed: %s", s.url, exc)
        return s
    updates: dict[str, object] = {}
    if "description" in candidates and not s.description:
        updates["description"] = candidates["description"]
    if "image_url" in candidates and candidates["image_url"]:
        updates["image_url"] = candidates["image_url"]
    if "price_min" in candidates and s.price_min is None:
        updates["price_min"] = candidates["price_min"]
    if "price_max" in candidates and s.price_max is None:
        updates["price_max"] = candidates["price_max"]
    if not updates:
        return s
    return s.model_copy(update=updates)
