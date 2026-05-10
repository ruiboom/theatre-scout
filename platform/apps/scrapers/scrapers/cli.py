"""`scrape` CLI."""

from __future__ import annotations

import logging
import sys

import typer

from .adapters import REGISTRY
from .runner import run_all, run_one

app = typer.Typer(help="Scrape London theatre listings into the platform DB.")


@app.command("list")
def list_venues() -> None:
    """List registered venue adapters."""
    for slug, cls in sorted(REGISTRY.items()):
        typer.echo(f"  {slug:24}  {cls.__name__}")
    typer.echo(f"\n{len(REGISTRY)} adapter(s) registered")


@app.command("venue")
def scrape_venue(slug: str) -> None:
    """Scrape a single venue."""
    _setup_logging()
    result = run_one(slug)
    typer.echo(result)
    if result["status"] == "failed":
        sys.exit(1)


@app.command("all")
def scrape_all(max_workers: int = 6) -> None:
    """Scrape every registered adapter in parallel."""
    _setup_logging()
    results = run_all(max_workers=max_workers)
    failed = [r for r in results if r["status"] == "failed"]
    typer.echo(f"\nDone. {len(results) - len(failed)} success, {len(failed)} failed.")
    for r in failed:
        typer.echo(f"  ✗ {r['slug']}: {r.get('error')}")
    if failed:
        sys.exit(1)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


if __name__ == "__main__":
    app()
