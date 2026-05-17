"""`scrape` CLI. Mirrors scout's flag set so muscle memory ports across.

scrape list                                              list registered adapters
scrape venue <slug> [--enrich] [--replace] [--workers N] one venue
scrape all          [--enrich] [--replace] [--workers N] every venue
scrape sync-venues <theatres.yaml>                       upsert venues from YAML
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
import yaml

from .adapters import all_adapters, load_all
from .http import Client
from .models import Theatre
from .runner import run_all, run_one
from .writer import upsert_theatres

app = typer.Typer(
    help="Scrape London theatre listings into the platform DB.",
    no_args_is_help=True,
)


@app.command("list")
def list_venues() -> None:
    """List registered venue adapters."""
    load_all()
    for cls in all_adapters():
        flag = " (js)" if cls.requires_js else ""
        typer.echo(f"  {cls.slug:32}  {cls.__name__}{flag}")
    typer.echo(f"\n{len(all_adapters())} adapter(s) registered")


@app.command("venue")
def scrape_venue(
    slug: str,
    enrich: bool = typer.Option(False, "--enrich", help="Fetch each show's detail page."),
    replace: bool = typer.Option(
        False, "--replace", help="Wipe existing rows for this venue first."
    ),
    workers: int = typer.Option(1, "--workers", help="Parallel workers for the enrich step."),
) -> None:
    """Scrape a single venue."""
    _setup_logging()
    with Client() as client:
        run = run_one(slug, client, enrich=enrich, replace=replace, workers=workers)
    typer.echo(run.model_dump_json())
    if run.status == "failed":
        sys.exit(1)


@app.command("all")
def scrape_all(
    enrich: bool = typer.Option(False, "--enrich", help="Fetch each show's detail page."),
    replace: bool = typer.Option(False, "--replace", help="Wipe existing rows per venue first."),
    workers: int = typer.Option(1, "--workers", help="Parallel workers for the enrich step."),
) -> None:
    """Scrape every registered adapter (3-phase pipeline)."""
    _setup_logging()
    with Client() as client:
        runs = run_all(client, enrich=enrich, replace=replace, workers=workers)
    failed = [r for r in runs if r.status == "failed"]
    success = len(runs) - len(failed)
    typer.echo(f"\nDone. {success} success, {len(failed)} failed.")
    for r in failed:
        typer.echo(f"  ✗ {r.theatre_slug}: {r.error}")
    # Exit semantics tuned for cron use: a few flaky venues (DNS, anti-bot) is
    # expected and shouldn't fail the job. Only exit 1 if the run was
    # catastrophic — every adapter failed (likely a systemic issue: network
    # down, Postgres unreachable, browser missing). Per-venue failures live
    # in the scrape_runs table for inspection.
    if runs and not success:
        sys.exit(1)


@app.command("sync-venues")
def sync_venues(yaml_path: Path) -> None:
    """Upsert venues from a theatres.yaml file (same format as scout's).

    Also reads the sibling `theatre-coords.yaml` so venue map coordinates flow
    to the live site through the normal daily sync — not just the one-shot
    scout ETL. (This is the path that was missing: new venues had no `location`
    until it was wired here.)
    """
    _setup_logging()
    with yaml_path.open() as f:
        data = yaml.safe_load(f) or []
    theatres = [Theatre(**row) for row in data]
    coords = _load_coords(yaml_path.parent / "theatre-coords.yaml")
    n = upsert_theatres(theatres, coords)
    typer.echo(f"Upserted {n} venues from {yaml_path} ({len(coords)} with coords)")


def _load_coords(path: Path) -> dict[str, tuple[float, float]]:
    """slug -> (lat, lon) from theatre-coords.yaml. Missing file -> {}.

    Tolerates both the `{lat, lon}` mapping form scout writes and a bare
    `[lat, lon]` list, mirroring scripts/etl_from_scout.py.
    """
    if not path.exists():
        return {}
    with path.open() as f:
        raw = yaml.safe_load(f) or {}
    out: dict[str, tuple[float, float]] = {}
    for slug, val in raw.items():
        if isinstance(val, dict):
            lat = val.get("lat")
            lon = val.get("lon")
            if lon is None:
                lon = val.get("lng")
            if lat is not None and lon is not None:
                out[slug] = (float(lat), float(lon))
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            out[slug] = (float(val[0]), float(val[1]))
    return out


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


if __name__ == "__main__":
    app()
