from __future__ import annotations

import os
import sqlite3
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from datetime import date as Date
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scout import db
from scout.models import Show, Theatre
from scout.theatres import load as load_theatres

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "theatre-scout.db"
DEFAULT_THEATRES_PATH = ROOT / "theatres.yaml"

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


def get_conn(db_path: Path = Depends(get_db_path)) -> Iterator[sqlite3.Connection]:
    conn = db.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def _layout_ctx(conn: sqlite3.Connection) -> dict[str, object]:
    """Context vars expected by base.html. Merged into every template response."""
    return {"last_refresh": db.last_scrape_at(conn)}


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
    show_counts = Counter(s.theatre_slug for s in upcoming)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **_layout_ctx(conn),
            "by_cat": by_cat,
            "show_counts": show_counts,
            "total_shows": len(upcoming),
        },
    )


@app.get("/theatres/{slug}")
def theatre_page(
    slug: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    theatres_path: Path = Depends(get_theatres_path),
) -> object:
    theatres = {t.slug: t for t in load_theatres(theatres_path)}
    if slug not in theatres:
        raise HTTPException(status_code=404, detail=f"Unknown theatre: {slug}")
    shows = db.query_by_theatre(conn, slug)
    return templates.TemplateResponse(
        request,
        "theatre.html",
        {**_layout_ctx(conn), "theatre": theatres[slug], "shows": shows},
    )


SORT_FIELDS = {"start_date", "end_date", "title", "venue"}


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

    def _pill_url(when_value: str) -> str:
        parts: list[str] = []
        if q:
            parts.append(f"q={q}")
        if type:
            parts.append(f"type={type}")
        if cat:
            parts.append(f"cat={cat}")
        if when_value:
            parts.append(f"when={when_value}")
        if sort:
            parts.append(f"sort={sort}")
        if dir:
            parts.append(f"dir={dir}")
        return "/shows" + ("?" + "&".join(parts) if parts else "")

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
            "pill_urls": {
                "": _pill_url(""),
                "today": _pill_url("today"),
                "week": _pill_url("week"),
                "new": _pill_url("new"),
            },
        },
    )


@app.post("/refresh")
def refresh(
    conn: sqlite3.Connection = Depends(get_conn),
) -> RedirectResponse:
    from scout import adapters, scraper
    from scout.http import Client

    adapters.load_all()
    scraper.run_all(Client(), conn)
    return RedirectResponse("/", status_code=303)
