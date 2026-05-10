"""Postgres writes for the ingest pipeline.

Maps the adapter-facing `Show` (scout-shaped: theatre_slug, url, price_min/max
in pence) onto the platform DB columns (venue_id, booking_url,
price_min_pence/price_max_pence). The translation lives only here so adapters
never need to know what the DB column is called.

`write_shows(slug, shows, replace=...)` is the per-venue write. With
`replace=True` it preserves prior `first_seen_at` keyed by `booking_url` so the
"new shows" query keeps working when a bespoke adapter changes title shape.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable

import psycopg

from .models import ScrapeRun, Show, Theatre
from .text import slugify

log = logging.getLogger(__name__)


def _conn() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url, autocommit=False)


# ---- venues -----------------------------------------------------------------


def upsert_theatres(theatres: Iterable[Theatre]) -> int:
    """Idempotent venue upsert. Run once at startup, before any show writes."""
    n = 0
    with _conn() as conn, conn.cursor() as cur:
        for t in theatres:
            cur.execute(
                """
                INSERT INTO venues (slug, name, neighbourhood, postcode_prefix, category, website)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name             = EXCLUDED.name,
                    neighbourhood    = EXCLUDED.neighbourhood,
                    postcode_prefix  = EXCLUDED.postcode_prefix,
                    category         = EXCLUDED.category,
                    website          = EXCLUDED.website
                """,
                (t.slug, t.name, t.area, t.postcode_prefix, t.category, str(t.url)),
            )
            n += 1
        conn.commit()
    return n


# ---- shows ------------------------------------------------------------------


def write_shows(theatre_slug: str, shows: Iterable[Show], *, replace: bool) -> int:
    """Insert shows for a single theatre.

    With `replace=True`, the existing rows for the venue are wiped first so that
    titles which dropped off the listings page disappear from the database too.
    Prior `first_seen_at` is preserved keyed by booking URL so a re-titled
    bespoke adapter doesn't reset the "new this week" signal.
    """
    written = 0
    with _conn() as conn, conn.cursor() as cur:
        venue_id = _venue_id_for(cur, theatre_slug)
        if venue_id is None:
            log.warning("unknown theatre_slug=%s — skipping write", theatre_slug)
            return 0

        prior_first_seen: dict[str, str] = {}
        if replace:
            prior_first_seen = _first_seen_by_url(cur, venue_id)
            cur.execute("DELETE FROM shows WHERE venue_id = %s", (venue_id,))

        for s in list(shows):
            cur.execute(
                """
                INSERT INTO shows (
                    slug, venue_id, title, show_type,
                    description_short, description_full,
                    price_min_pence, price_max_pence,
                    start_date, end_date,
                    duration_minutes, age_rating, content_warnings,
                    image_url, booking_url,
                    writer, director, cast_members,
                    raw_data,
                    first_seen_at, last_seen_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s,
                    COALESCE(%s, NOW()), NOW()
                )
                ON CONFLICT (venue_id, title, start_date) DO UPDATE SET
                    description_short = EXCLUDED.description_short,
                    description_full  = EXCLUDED.description_full,
                    price_min_pence   = EXCLUDED.price_min_pence,
                    price_max_pence   = EXCLUDED.price_max_pence,
                    end_date          = EXCLUDED.end_date,
                    duration_minutes  = EXCLUDED.duration_minutes,
                    age_rating        = EXCLUDED.age_rating,
                    content_warnings  = EXCLUDED.content_warnings,
                    image_url         = EXCLUDED.image_url,
                    booking_url       = EXCLUDED.booking_url,
                    writer            = EXCLUDED.writer,
                    director          = EXCLUDED.director,
                    cast_members      = EXCLUDED.cast_members,
                    raw_data          = EXCLUDED.raw_data,
                    last_seen_at      = NOW()
                """,
                (
                    _slug_for(s),
                    venue_id,
                    s.title,
                    s.show_type,
                    s.description,                         # short
                    s.description_full or s.description,   # full ≥ short
                    s.price_min,
                    s.price_max,
                    s.start_date,
                    s.end_date,
                    s.duration_minutes,
                    s.age_rating,
                    list(s.content_warnings),
                    str(s.image_url) if s.image_url else None,
                    str(s.url),
                    s.writer,
                    s.director,
                    list(s.cast_members),
                    json.dumps(s.raw),
                    prior_first_seen.get(str(s.url)),
                ),
            )
            written += 1
        conn.commit()
    return written


def _slug_for(s: Show) -> str:
    """Stable slug for the URL part of /shows/<slug>. Composed from the venue
    slug + title so that a returning production in a later season stays unique
    if the title shape is identical."""
    base = slugify(f"{s.theatre_slug}-{s.title}")[:120]
    if s.start_date is not None:
        base = f"{base}-{s.start_date.year}"
    return base


def _venue_id_for(cur: psycopg.Cursor, slug: str) -> str | None:
    cur.execute("SELECT id FROM venues WHERE slug = %s", (slug,))
    row = cur.fetchone()
    return row[0] if row else None


def _first_seen_by_url(cur: psycopg.Cursor, venue_id: str) -> dict[str, str]:
    cur.execute(
        "SELECT booking_url, first_seen_at FROM shows WHERE venue_id = %s",
        (venue_id,),
    )
    return {url: ts.isoformat() for url, ts in cur.fetchall() if url}


# ---- runs -------------------------------------------------------------------


def record_run(run: ScrapeRun) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scrape_runs
              (venue_slug, started_at, finished_at, status, shows_found, error)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                run.theatre_slug,
                run.started_at,
                run.finished_at,
                run.status,
                run.shows_found,
                run.error,
            ),
        )
        conn.commit()
