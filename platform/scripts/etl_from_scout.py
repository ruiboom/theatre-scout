"""One-shot ETL: scout/ SQLite -> platform Postgres.

Seeds the platform DB with real data without waiting for every scout adapter
to be ported. Reads scout's `data/theatre-scout.db` plus
`theatre-coords.yaml` for venue lat/lon, and bulk-loads venues + shows.

Idempotent: drops every existing row in the platform DB's listings tables and
rewrites them from scratch. Run again any time scout has fresher data.

Usage (from platform/):
  uv run --directory apps/scrapers \
    python scripts/etl_from_scout.py \
    --sqlite ../../data/theatre-scout.db \
    --theatres ../../theatres.yaml \
    --coords   ../../theatre-coords.yaml \
    --postgres "postgresql://postgres:postgres@localhost:5433/listings"
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

import psycopg
import yaml


def slugify(value: str) -> str:
    folded = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    out = []
    last_dash = False
    for ch in folded:
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, type=Path)
    ap.add_argument("--theatres", required=True, type=Path, help="theatres.yaml")
    ap.add_argument("--coords", type=Path, help="theatre-coords.yaml (optional)")
    ap.add_argument("--postgres", required=True, help="DATABASE_URL for the platform DB")
    args = ap.parse_args()

    if not args.sqlite.exists():
        print(f"sqlite not found: {args.sqlite}", file=sys.stderr)
        return 1
    if not args.theatres.exists():
        print(f"theatres.yaml not found: {args.theatres}", file=sys.stderr)
        return 1

    # ---- read scout side ----
    with args.theatres.open() as f:
        theatres_yaml = yaml.safe_load(f) or []
    coords_map: dict[str, tuple[float, float]] = {}
    if args.coords and args.coords.exists():
        with args.coords.open() as f:
            raw = yaml.safe_load(f) or {}
        for slug, val in raw.items():
            # tolerate both [lat, lon] and {lat, lon}
            if isinstance(val, list) and len(val) >= 2:
                coords_map[slug] = (float(val[0]), float(val[1]))
            elif isinstance(val, dict) and "lat" in val and ("lon" in val or "lng" in val):
                coords_map[slug] = (
                    float(val["lat"]),
                    float(val.get("lon") or val.get("lng")),
                )

    sql_path = args.sqlite
    s = sqlite3.connect(f"file:{sql_path}?mode=ro", uri=True)
    s.row_factory = sqlite3.Row
    scout_shows = list(
        s.execute(
            """
            SELECT theatre_slug, title, show_type, description, url,
                   start_date, end_date, price_min, price_max, image_url,
                   raw, first_seen_at, last_seen_at
              FROM shows
            """
        )
    )
    s.close()
    print(f"scout: {len(theatres_yaml)} theatres, {len(scout_shows)} shows", flush=True)

    # ---- write platform side ----
    with psycopg.connect(args.postgres, autocommit=False) as conn, conn.cursor() as cur:
        # Wipe listings tables. CASCADE clears performances + show_tags via FK.
        cur.execute("TRUNCATE TABLE shows, scrape_runs RESTART IDENTITY CASCADE")
        cur.execute("TRUNCATE TABLE venues RESTART IDENTITY CASCADE")
        cur.execute("DELETE FROM tags")  # tags has no FK in -> just delete rows

        # ---- venues ----
        venue_id_by_slug: dict[str, str] = {}
        for t in theatres_yaml:
            slug = t["slug"]
            lat_lon = coords_map.get(slug)
            location = (
                None
                if lat_lon is None
                else psycopg.sql.SQL("ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography")
            )
            if lat_lon is None:
                cur.execute(
                    """
                    INSERT INTO venues
                      (slug, name, neighbourhood, postcode_prefix, category, website)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        slug,
                        t["name"],
                        t["area"],
                        t.get("postcode_prefix"),
                        t["category"],
                        t["url"],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO venues
                      (slug, name, neighbourhood, postcode_prefix, category, website, location)
                    VALUES
                      (%s, %s, %s, %s, %s, %s,
                       ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
                    RETURNING id
                    """,
                    (
                        slug,
                        t["name"],
                        t["area"],
                        t.get("postcode_prefix"),
                        t["category"],
                        t["url"],
                        lat_lon[1],  # lng
                        lat_lon[0],  # lat
                    ),
                )
            venue_id_by_slug[slug] = cur.fetchone()[0]
        print(f"venues: inserted {len(venue_id_by_slug)}", flush=True)

        # ---- shows ----
        wrote = 0
        skipped = 0
        for r in scout_shows:
            venue_id = venue_id_by_slug.get(r["theatre_slug"])
            if venue_id is None:
                skipped += 1
                continue
            base_slug = slugify(f"{r['theatre_slug']}-{r['title']}")[:120]
            slug = f"{base_slug}-{r['start_date'][:4]}" if r["start_date"] else base_slug
            try:
                raw = json.loads(r["raw"]) if r["raw"] else {}
            except Exception:
                raw = {}
            cur.execute(
                """
                INSERT INTO shows (
                    slug, venue_id, title, show_type,
                    description_short, description_full,
                    price_min_pence, price_max_pence,
                    start_date, end_date,
                    image_url, booking_url,
                    raw_data,
                    first_seen_at, last_seen_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s,
                    %s, %s
                )
                ON CONFLICT (slug) DO NOTHING
                """,
                (
                    slug,
                    venue_id,
                    r["title"],
                    r["show_type"] or "other",
                    r["description"] or "",
                    r["description"] or "",
                    r["price_min"],
                    r["price_max"],
                    r["start_date"],
                    r["end_date"],
                    r["image_url"],
                    r["url"],
                    json.dumps(raw),
                    r["first_seen_at"] or None,
                    r["last_seen_at"] or None,
                ),
            )
            wrote += 1
        print(f"shows: inserted {wrote}, skipped {skipped} (unknown venue)", flush=True)

        # Faux scrape_runs row so the layout's "Last refreshed" stamp shows
        # something sensible without us having to fake the per-venue runs.
        cur.execute(
            """
            INSERT INTO scrape_runs
              (venue_slug, started_at, finished_at, status, shows_found)
            VALUES (%s, NOW(), NOW(), %s, %s)
            """,
            ("etl-from-scout", "success", wrote),
        )

        conn.commit()
    print("done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
