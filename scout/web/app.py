from __future__ import annotations

import os
import sqlite3
import threading
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from datetime import date as Date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scout import coords as coords_mod
from scout import db
from scout.models import Show, Theatre
from scout.theatres import load as load_theatres

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "theatre-scout.db"
DEFAULT_THEATRES_PATH = ROOT / "theatres.yaml"
DEFAULT_COORDS_PATH = ROOT / "theatre-coords.yaml"

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.filters["fmt_date"] = lambda d: d.strftime("%a %d %b %Y") if d else ""
templates.env.filters["fmt_price"] = lambda p: (
    f"£{p / 100:.2f}" if isinstance(p, int) and p > 0 else ""
)


def _fmt_relative(when: datetime | None, *, now: datetime | None = None) -> str:
    if when is None:
        return "never"
    now = now or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    delta = now - when
    secs = int(delta.total_seconds())
    if secs < 0:
        return "just now"
    if secs < 60:
        return "just now"
    if secs < 3600:
        m = secs // 60
        return f"{m}m ago"
    if secs < 86400:
        h = secs // 3600
        return f"{h}h ago"
    if secs < 86400 * 7:
        d = secs // 86400
        return f"{d}d ago"
    return when.strftime("%-d %b")


templates.env.filters["fmt_relative"] = _fmt_relative

app = FastAPI(title="Theatre Scout")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def get_db_path() -> Path:
    return Path(os.environ.get("SCOUT_DB_PATH") or DEFAULT_DB_PATH)


def get_theatres_path() -> Path:
    return Path(os.environ.get("SCOUT_THEATRES_PATH") or DEFAULT_THEATRES_PATH)


def get_coords_path(theatres_path: Path = Depends(get_theatres_path)) -> Path:
    explicit = os.environ.get("SCOUT_COORDS_PATH")
    if explicit:
        return Path(explicit)
    # Default: a sidecar next to theatres.yaml.
    return theatres_path.parent / "theatre-coords.yaml"


def get_conn(db_path: Path = Depends(get_db_path)) -> Iterator[sqlite3.Connection]:
    conn = db.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


# Background-scrape state. Module-level so concurrent /refresh clicks deduplicate
# without spinning up a second scrape on top of one already running.
_scrape_lock = threading.Lock()
_scrape_running = False
# Tunable defaults for the Refresh button. The web flow does the full,
# enriched, replace-stale, parallel scrape — same as `scout scrape --enrich
# --replace --workers 16` from the CLI.
REFRESH_ENRICH = True
REFRESH_REPLACE = True
REFRESH_WORKERS = 16


def is_scrape_running() -> bool:
    return _scrape_running


def _layout_ctx(conn: sqlite3.Connection) -> dict[str, object]:
    """Context vars expected by base.html. Merged into every template response."""
    return {
        "last_refresh": db.last_scrape_at(conn),
        "scrape_running": is_scrape_running(),
    }


@app.get("/")
def home(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    theatres_path: Path = Depends(get_theatres_path),
) -> object:
    theatres = load_theatres(theatres_path)
    upcoming = db.query_upcoming(conn, today=Date.today())
    by_cat: dict[str, list] = {"major": [], "mid": [], "fringe": [], "outer": []}  # type: ignore[type-arg]
    for t in theatres:
        by_cat[t.category].append(t)
    # Sort venue names case-insensitively, ignoring a leading "The " so
    # "The Yard" lands under Y rather than T.
    sorted_theatres = sorted(theatres, key=lambda t: t.name.lower().removeprefix("the ").strip())
    show_counts = Counter(s.theatre_slug for s in upcoming)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **_layout_ctx(conn),
            "by_cat": by_cat,
            "theatres": sorted_theatres,
            "show_counts": show_counts,
            "total_shows": len(upcoming),
            "total_venues": len(theatres),
        },
    )


@app.get("/theatres/{slug}")
def theatre_page(
    slug: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    theatres_path: Path = Depends(get_theatres_path),
    coords_path: Path = Depends(get_coords_path),
) -> object:
    theatres = {t.slug: t for t in load_theatres(theatres_path)}
    if slug not in theatres:
        raise HTTPException(status_code=404, detail=f"Unknown theatre: {slug}")
    shows = db.query_by_theatre(conn, slug)
    coord = coords_mod.load(coords_path).get(slug)
    return templates.TemplateResponse(
        request,
        "theatre.html",
        {
            **_layout_ctx(conn),
            "theatre": theatres[slug],
            "shows": shows,
            "coord": coord,
        },
    )


SORT_FIELDS = {"start_date", "end_date", "title", "venue"}
VIEW_MODES = {"rails", "list"}
RAIL_CATEGORIES: tuple[str, ...] = ("major", "mid", "fringe", "outer")
RAIL_PICK_LIMIT = 4


def _sort_shows(
    shows: Sequence[Show],
    theatres: Mapping[str, Theatre],
    field: str,
    descending: bool,
) -> list[Show]:
    from datetime import date

    far_future = date(9999, 1, 1)
    far_past = date(1, 1, 1)
    sentinel = far_past if descending else far_future

    def key(s: Show) -> Any:
        if field == "title":
            return s.title.lower()
        if field == "venue":
            t = theatres.get(s.theatre_slug)
            return t.name.lower() if t else ""
        if field == "end_date":
            return s.end_date or sentinel
        return s.start_date or sentinel

    return sorted(shows, key=key, reverse=descending)


@app.get("/shows")
def shows_page(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    theatres_path: Path = Depends(get_theatres_path),
    today: str | None = None,
    q: str | None = None,
    type: str | None = None,
    cat: str | None = None,
    when: str | None = None,
    sort: str | None = None,
    dir: str | None = None,
    view: str | None = None,
) -> object:
    cutoff = Date.fromisoformat(today) if today else Date.today()
    if when == "new":
        shows = db.query_new_shows(conn)
    else:
        shows = db.query_upcoming(conn, today=cutoff)
        if when == "today":
            shows = [
                s
                for s in shows
                if s.start_date is not None
                and s.start_date <= cutoff
                and (s.end_date is None or s.end_date >= cutoff)
            ]
        elif when == "week":
            week_end = cutoff + timedelta(days=7)
            shows = [
                s
                for s in shows
                if s.start_date is not None
                and s.start_date <= week_end
                and (s.end_date is None or s.end_date >= cutoff)
            ]
    theatres = {t.slug: t for t in load_theatres(theatres_path)}
    if q:
        needle = q.lower()
        shows = [s for s in shows if needle in s.title.lower()]
    if type:
        shows = [s for s in shows if s.show_type == type]
    if cat:
        shows = [
            s
            for s in shows
            if s.theatre_slug in theatres and theatres[s.theatre_slug].category == cat
        ]

    sort_field = sort if sort in SORT_FIELDS else "start_date"
    descending = dir == "desc"
    shows = _sort_shows(shows, theatres, sort_field, descending)

    view_mode = view if view in VIEW_MODES else "rails"

    rails: dict[str, dict[str, object]] = {}
    for c in RAIL_CATEGORIES:
        cat_shows = [
            s
            for s in shows
            if s.theatre_slug in theatres and theatres[s.theatre_slug].category == c
        ]
        rails[c] = {"total": len(cat_shows), "picks": cat_shows[:RAIL_PICK_LIMIT]}

    current_params: dict[str, str] = {
        "q": q or "",
        "type": type or "",
        "cat": cat or "",
        "when": when or "",
        "view": view_mode,
        "sort": sort_field if sort_field != "start_date" else "",
        "dir": "desc" if descending else "",
    }

    def chip_url(**changes: str) -> str:
        merged = {**current_params, **changes}
        # Drop the default view so the URL is clean when nothing is selected.
        if merged.get("view") == "rails":
            merged["view"] = ""
        cleaned = {k: v for k, v in merged.items() if v}
        return "/shows" + (("?" + urlencode(cleaned)) if cleaned else "")

    def sort_url(field: str) -> str:
        if sort_field == field:
            new_dir = "asc" if descending else "desc"
        else:
            new_dir = "asc"
        return chip_url(sort=field, dir=new_dir if new_dir != "asc" else "")

    # Hidden inputs for the search form: preserve everything except q.
    carry_params = [(k, v) for k, v in current_params.items() if v and k != "q"]

    return templates.TemplateResponse(
        request,
        "shows.html",
        {
            **_layout_ctx(conn),
            "shows": shows,
            "theatres": theatres,
            "q": q or "",
            "filter_type": type or "",
            "filter_cat": cat or "",
            "filter_when": when or "",
            "sort_field": sort_field,
            "sort_dir": "desc" if descending else "asc",
            "view": view_mode,
            "rails": rails,
            "chip_url": chip_url,
            "sort_url": sort_url,
            "carry_params": carry_params,
        },
    )


@app.post("/refresh")
def refresh(
    db_path: Path = Depends(get_db_path),
    theatres_path: Path = Depends(get_theatres_path),
) -> RedirectResponse:
    """Kick off a full scrape in a background thread; the request returns immediately.

    Concurrent clicks dedupe via `_scrape_running` — a second click while one is
    already in flight is silently ignored. Status is surfaced via `is_scrape_running()`
    in the layout context so the header can show "Scraping..." until it finishes.
    """
    global _scrape_running
    with _scrape_lock:
        if _scrape_running:
            return RedirectResponse("/", status_code=303)
        _scrape_running = True
    try:
        threading.Thread(
            target=_run_full_scrape, args=(db_path, theatres_path), daemon=True
        ).start()
    except Exception:
        _scrape_running = False
        raise
    return RedirectResponse("/", status_code=303)


def _run_full_scrape(db_path: Path, theatres_path: Path) -> None:
    """Worker body for the background refresh. Resets `_scrape_running` on exit
    so the UI's 'Scraping…' indicator clears even if the run fails."""
    global _scrape_running
    try:
        from scout import adapters, scraper
        from scout.http import Client

        adapters.load_all()
        conn = db.connect(db_path)
        try:
            db.init_schema(conn)
            db.upsert_theatres(conn, load_theatres(theatres_path))
            with Client() as client:
                scraper.run_all(
                    client,
                    conn,
                    enrich=REFRESH_ENRICH,
                    replace=REFRESH_REPLACE,
                    workers=REFRESH_WORKERS,
                )
        finally:
            conn.close()
    except Exception:
        import logging

        logging.getLogger(__name__).exception("background scrape failed")
        raise
    finally:
        _scrape_running = False
