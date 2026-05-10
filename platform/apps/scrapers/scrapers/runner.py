"""
Orchestrator. Loads adapters, dispatches them across distinct domains in
parallel, records ScrapeRuns. One adapter raising never crashes the run.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from .adapters import REGISTRY, get_adapter
from .base import BaseAdapter
from .writer import record_run, write_shows

log = logging.getLogger(__name__)


def run_one(slug: str) -> dict:
    """Scrape a single venue. Records a ScrapeRun. Never raises."""
    adapter = get_adapter(slug)
    return _execute(adapter)


def run_all(*, max_workers: int = 6) -> list[dict]:
    """Scrape every registered adapter in parallel."""
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_execute, cls()): slug for slug, cls in REGISTRY.items()}
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def _execute(adapter: BaseAdapter) -> dict:
    started = datetime.now(UTC)
    log.info("scraping %s", adapter.slug)
    try:
        shows = list(adapter.fetch())
        written = write_shows(shows)
        record_run(
            adapter.slug,
            started_at=started,
            finished_at=datetime.now(UTC),
            status="success" if written == len(shows) else "partial",
            shows_found=written,
        )
        return {"slug": adapter.slug, "status": "success", "shows": written}
    except Exception as err:  # adapter failure must not bring the run down
        log.exception("adapter %s failed", adapter.slug)
        record_run(
            adapter.slug,
            started_at=started,
            finished_at=datetime.now(UTC),
            status="failed",
            shows_found=0,
            error=str(err),
        )
        return {"slug": adapter.slug, "status": "failed", "error": str(err)}
