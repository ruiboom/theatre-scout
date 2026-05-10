"""
Writes normalised ScrapedShow records into Postgres.

Idempotent: same input twice produces the same DB state. Uses an upsert on
(venue_id, title) — that's the natural key.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable

import psycopg

from .models import ScrapedShow

log = logging.getLogger(__name__)


def _conn() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url, autocommit=False)


def write_shows(shows: Iterable[ScrapedShow]) -> int:
    """Upsert every show + its performances. Returns count written."""
    written = 0
    with _conn() as conn, conn.cursor() as cur:
        for show in shows:
            venue_id = _venue_id_for(cur, show.venue_slug)
            if venue_id is None:
                log.warning("unknown venue_slug=%s — skipping show %r",
                            show.venue_slug, show.title)
                continue

            cur.execute(
                """
                INSERT INTO shows (
                    slug, venue_id, title, show_type,
                    description_short, description_full,
                    price_min_pence, price_max_pence,
                    duration_minutes, age_rating, content_warnings,
                    image_url, booking_url,
                    writer, director, cast_members,
                    raw_data, last_seen_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, NOW()
                )
                ON CONFLICT (venue_id, title) DO UPDATE SET
                    description_short = EXCLUDED.description_short,
                    description_full  = EXCLUDED.description_full,
                    price_min_pence   = EXCLUDED.price_min_pence,
                    price_max_pence   = EXCLUDED.price_max_pence,
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
                RETURNING id
                """,
                (
                    show.slug, venue_id, show.title, show.show_type,
                    show.description_short, show.description_full,
                    show.price_min_pence, show.price_max_pence,
                    show.duration_minutes, show.age_rating, show.content_warnings,
                    show.image_url, show.booking_url,
                    show.writer, show.director, show.cast_members,
                    json.dumps(show.raw_data),
                ),
            )
            row = cur.fetchone()
            if row is None:
                continue
            show_id = row[0]
            _upsert_performances(cur, show_id, show)
            _upsert_tags(cur, show_id, show)
            written += 1
        conn.commit()
    return written


def _venue_id_for(cur: psycopg.Cursor, slug: str) -> str | None:
    cur.execute("SELECT id FROM venues WHERE slug = %s", (slug,))
    row = cur.fetchone()
    return row[0] if row else None


def _upsert_performances(cur: psycopg.Cursor, show_id: str, show: ScrapedShow) -> None:
    for p in show.performances:
        cur.execute(
            """
            INSERT INTO performances (
                show_id, starts_at, available_tickets_estimate, sold_out, raw_data
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (show_id, starts_at) DO UPDATE SET
                available_tickets_estimate = EXCLUDED.available_tickets_estimate,
                sold_out                   = EXCLUDED.sold_out,
                raw_data                   = EXCLUDED.raw_data
            """,
            (
                show_id, p.starts_at, p.available_tickets_estimate,
                p.sold_out, json.dumps(p.raw_data),
            ),
        )


def _upsert_tags(cur: psycopg.Cursor, show_id: str, show: ScrapedShow) -> None:
    for slug in show.genres:
        _attach_tag(cur, show_id, slug, "genre")
    for slug in show.tags:
        _attach_tag(cur, show_id, slug, "tag")


def _attach_tag(cur: psycopg.Cursor, show_id: str, slug: str, tag_type: str) -> None:
    cur.execute(
        """
        INSERT INTO tags (slug, name, type)
        VALUES (%s, %s, %s)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (slug, slug.replace("-", " ").title(), tag_type),
    )
    row = cur.fetchone()
    if row:
        tag_id = row[0]
    else:
        cur.execute("SELECT id FROM tags WHERE slug = %s", (slug,))
        tag_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO show_tags (show_id, tag_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (show_id, tag_id),
    )


def record_run(
    venue_slug: str,
    *,
    started_at,
    finished_at,
    status: str,
    shows_found: int,
    error: str | None = None,
) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scrape_runs
              (venue_slug, started_at, finished_at, status, shows_found, error)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (venue_slug, started_at, finished_at, status, shows_found, error),
        )
        conn.commit()
