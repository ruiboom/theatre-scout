from __future__ import annotations

import os
import sqlite3
from collections import Counter
from collections.abc import Iterator
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scout import db
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
        request, "theatre.html", {"theatre": theatres[slug], "shows": shows}
    )


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
        return "/shows" + ("?" + "&".join(parts) if parts else "")

    return templates.TemplateResponse(
        request,
        "shows.html",
        {
            "shows": shows,
            "theatres": theatres,
            "q": q or "",
            "filter_type": type or "",
            "filter_cat": cat or "",
            "filter_when": when or "",
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
