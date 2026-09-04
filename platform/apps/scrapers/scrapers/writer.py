"""Postgres writes for the ingest pipeline.

Maps the adapter-facing `Show` (scout-shaped: theatre_slug, url, price_min/max
in pence) onto the platform DB columns (venue_id, booking_url,
price_min_pence/price_max_pence). The translation lives only here so adapters
never need to know what the DB column is called.

`write_shows(slug, shows, replace=...)` is the per-venue write. With
`replace=True` it deletes rows that dropped off the listing and upserts the
rest in place (stable ids, honest `updated_at`), preserving prior
`first_seen_at` keyed by `booking_url` for any row it has to re-create.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Iterable, Mapping

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


def upsert_theatres(
    theatres: Iterable[Theatre],
    coords: Mapping[str, tuple[float, float]] | None = None,
) -> int:
    """Idempotent venue upsert. Run once at startup, before any show writes.

    `coords` maps slug -> (lat, lon) (from theatre-coords.yaml). When a slug has
    coords we also write the PostGIS `location` point — and refresh it on
    conflict so the documented "add a venue" flow (theatres.yaml +
    theatre-coords.yaml -> sync-venues) carries map coordinates all the way to
    the live site. A slug with no coords leaves any existing `location`
    untouched (the UPDATE simply omits the column), so this never wipes a point.
    """
    coords = coords or {}
    n = 0
    with _conn() as conn, conn.cursor() as cur:
        for t in theatres:
            lat_lon = coords.get(t.slug)
            if lat_lon is None:
                cur.execute(
                    """
                    INSERT INTO venues
                      (slug, name, neighbourhood, postcode_prefix, category, website)
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
            else:
                lat, lon = lat_lon
                cur.execute(
                    """
                    INSERT INTO venues
                      (slug, name, neighbourhood, postcode_prefix, category, website,
                       location)
                    VALUES
                      (%s, %s, %s, %s, %s, %s,
                       ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
                    ON CONFLICT (slug) DO UPDATE SET
                        name             = EXCLUDED.name,
                        neighbourhood    = EXCLUDED.neighbourhood,
                        postcode_prefix  = EXCLUDED.postcode_prefix,
                        category         = EXCLUDED.category,
                        website          = EXCLUDED.website,
                        location         = EXCLUDED.location
                    """,
                    (
                        t.slug,
                        t.name,
                        t.area,
                        t.postcode_prefix,
                        t.category,
                        str(t.url),
                        lon,  # ST_MakePoint(x=lon, y=lat)
                        lat,
                    ),
                )
            n += 1
        conn.commit()
    return n


# ---- shows ------------------------------------------------------------------


def write_shows(theatre_slug: str, shows: Iterable[Show], *, replace: bool) -> int:
    """Upsert shows for a single theatre.

    With `replace=True`, rows that are no longer on the venue's listing are
    deleted so titles which dropped off the site disappear from the database
    too. Rows that ARE still listed are updated in place rather than deleted
    and re-inserted: they keep their `id`, `first_seen_at` and — thanks to the
    content-aware `shows_updated_at` trigger — their `updated_at` unless
    something visible changed. (The old wipe-and-rewrite stamped every show as
    modified daily, which the sitemap dutifully reported and every crawler
    dutifully re-crawled — see migration 0007.) Prior `first_seen_at` is still
    preserved keyed by booking URL for the rare row that has to be re-created.
    """
    written = 0
    shows = list(shows)
    with _conn() as conn, conn.cursor() as cur:
        venue_id = _venue_id_for(cur, theatre_slug)
        if venue_id is None:
            log.warning("unknown theatre_slug=%s — skipping write", theatre_slug)
            return 0

        # Guard against a transient empty scrape wiping a venue under --replace.
        # If the adapter found nothing this run (a site blip / anti-bot hiccup
        # during the daily run), deleting would blank the venue on the live site
        # until the next good scrape. Keep the last-known-good rows instead — the
        # next successful run refreshes them, and the venue-health monitor still
        # flags the zero so it's visible. A genuine emptying is harmless: those
        # rows have past end_dates and drop out of the date-filtered listings.
        if replace and not shows:
            existing = _count_shows(cur, venue_id)
            if existing:
                log.warning(
                    "%s: 0 shows parsed but %d already stored — skipping --replace "
                    "wipe (likely a transient fetch failure)",
                    theatre_slug,
                    existing,
                )
            return 0

        # Dedupe within a single run by slug. Adapters occasionally emit
        # near-duplicates (e.g. nav links matched as cards) that all collapse
        # to the same slug after URL hashing — first one wins.
        unique: list[tuple[str, Show]] = []
        seen_slugs: set[str] = set()
        for s in shows:
            slug = _slug_for(s)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            unique.append((slug, s))

        prior_first_seen: dict[str, str] = {}
        if replace:
            prior_first_seen = _first_seen_by_url(cur, venue_id)
            # Only rows that fell off the listing go. Everything still listed is
            # upserted below and keeps its identity.
            cur.execute(
                "DELETE FROM shows WHERE venue_id = %s AND NOT (slug = ANY(%s))",
                (venue_id, list(seen_slugs)),
            )

        for slug, s in unique:
            params = _insert_params(slug, venue_id, s, prior_first_seen)
            try:
                with conn.transaction():
                    cur.execute(_UPSERT_SQL, params)
            except psycopg.errors.UniqueViolation:
                # The natural key (venue, title, start_date) moved — typically a
                # date correction — but the slug (venue + title + year + URL
                # hash) didn't, so the upsert tried to insert a second row with
                # the same slug. Retire the old row and insert afresh; its
                # first_seen_at survives via the URL-keyed map.
                cur.execute(
                    "DELETE FROM shows WHERE venue_id = %s AND slug = %s",
                    (venue_id, slug),
                )
                cur.execute(_UPSERT_SQL, params)
            written += 1
        conn.commit()
    return written


_UPSERT_SQL = """
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
"""


def _insert_params(
    slug: str, venue_id: str, s: Show, prior_first_seen: Mapping[str, str]
) -> tuple[object, ...]:
    return (
        slug,
        venue_id,
        s.title,
        s.show_type,
        s.description,  # short
        s.description_full or s.description,  # full >= short
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
    )


def _slug_for(s: Show) -> str:
    """Stable slug for the URL part of /shows/<slug>.

    Composed from `venue + title (+ year)` plus a 6-char URL hash. The URL
    hash is what guarantees uniqueness — without it, an adapter that captures
    multiple distinct cards as the same human-friendly title (e.g. multiple
    nav links titled "What's On" with different hrefs) would collide.
    """
    base = slugify(f"{s.theatre_slug}-{s.title}")[:100]
    if s.start_date is not None:
        base = f"{base}-{s.start_date.year}"
    h = hashlib.sha1(str(s.url).encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}"


def _venue_id_for(cur: psycopg.Cursor, slug: str) -> str | None:
    cur.execute("SELECT id FROM venues WHERE slug = %s", (slug,))
    row = cur.fetchone()
    return row[0] if row else None


def _count_shows(cur: psycopg.Cursor, venue_id: str) -> int:
    cur.execute("SELECT COUNT(*) FROM shows WHERE venue_id = %s", (venue_id,))
    row = cur.fetchone()
    return int(row[0]) if row else 0


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


# ---- events retention -------------------------------------------------------


def prune_events(days: int = 90) -> int:
    """Delete analytics `events` rows older than `days`; return the count removed.

    The events table is unbounded by design — one row per tracked visit / search
    / outbound click — so without periodic pruning it grows forever, inflating
    DB size and backups. This runs from the daily scrape workflow, the one cron
    that already holds a direct Neon connection, so retention rides the same
    schedule as ingestion.
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM events WHERE occurred_at < NOW() - make_interval(days => %s)",
            (days,),
        )
        n = cur.rowcount
        conn.commit()
    return n
