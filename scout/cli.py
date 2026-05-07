from __future__ import annotations

import sqlite3
from pathlib import Path

import typer

from scout import __version__, adapters, db, scraper, theatres
from scout.http import Client
from scout.models import ScrapeRun

app = typer.Typer(
    help="Theatre Scout — local directory of London theatre shows.", no_args_is_help=True
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "theatre-scout.db"
THEATRES_PATH = ROOT / "theatres.yaml"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Theatre Scout CLI."""


def _open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(DB_PATH)
    db.init_schema(conn)
    db.upsert_theatres(conn, theatres.load(THEATRES_PATH))
    return conn


def _print_run(r: ScrapeRun) -> None:
    typer.echo(f"  {r.theatre_slug:<32}  {r.status:<7}  {r.shows_found:>3} shows  {r.error or ''}")


@app.command()
def scrape(
    theatre: str | None = typer.Option(
        None, "--theatre", help="Slug of a single theatre to scrape."
    ),
    enrich: bool = typer.Option(
        False,
        "--enrich",
        help="After listing scrape, fetch each show's detail page for a description (slow).",
    ),
) -> None:
    """Scrape one or all theatres and persist shows to the local DB."""
    adapters.load_all()
    conn = _open_db()
    client = Client()

    if theatre:
        run = scraper.run_one(theatre, client, conn, enrich=enrich)
        _print_run(run)
        raise typer.Exit(0 if run.status == "success" else 1)

    runs = scraper.run_all(client, conn, enrich=enrich)
    typer.echo(f"Scraped {len(runs)} theatres:")
    for r in runs:
        _print_run(r)
    failed = sum(1 for r in runs if r.status == "failed")
    succeeded = sum(1 for r in runs if r.status == "success")
    typer.echo(f"\n{succeeded} ok, {failed} failed")
    raise typer.Exit(1 if failed and succeeded == 0 else 0)


@app.command(name="list")
def list_theatres() -> None:
    """Print every known theatre."""
    for t in theatres.load(THEATRES_PATH):
        typer.echo(f"{t.slug:<32}  {t.category:<6}  {t.name}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to."),
    port: int = typer.Option(8000, help="Port to bind to."),
) -> None:
    """Launch the local web UI."""
    import uvicorn

    adapters.load_all()
    uvicorn.run("scout.web.app:app", host=host, port=port, reload=False)
