-- venues.active: drop a venue from the scrape + health monitor without deleting
-- it (reversible). `active` defaults TRUE; set it FALSE for venues whose sites
-- are unreachable so `venue_health` stops flagging them forever. The flag only
-- gates venue_health today — extend it to the public website queries later if a
-- dropped venue should also disappear from the directory/map.
--
-- Dropped 2026-06 (sites unreachable — not adapter bugs):
--   hen-and-chickens — henandchickens.com is dead; the operating company,
--                      Unrestricted View (unrestrictedview.co.uk), is JS-rendered
--                      and would need a fresh adapter.
--   tabard           — tabardtheatre.co.uk serves a self-signed TLS certificate,
--                      so the fetcher refuses the handshake.
-- Re-enable a venue: re-register its adapter (bulk.py or a module) and
--   UPDATE venues SET active = TRUE WHERE slug = '<slug>';
--
-- No migration runner — apply by hand, in numeric order:
--   psql "$DATABASE_URL" -f packages/db/migrations/0005_venue_active_flag.sql

BEGIN;

ALTER TABLE venues ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE venues SET active = FALSE WHERE slug IN ('hen-and-chickens', 'tabard');

-- Recreate venue_health with a trailing `WHERE v.active` so inactive venues
-- produce no row (the rest is identical to 0004 / schema.sql).
CREATE OR REPLACE VIEW venue_health AS
WITH latest AS (
    SELECT DISTINCT ON (venue_slug)
           venue_slug, status, shows_found, finished_at
      FROM scrape_runs
     ORDER BY venue_slug, started_at DESC
),
baseline AS (
    SELECT venue_slug,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY shows_found) AS median_found,
           MAX(shows_found) AS max_found,
           COUNT(*)         AS runs
      FROM scrape_runs
     WHERE status IN ('success', 'partial')
       AND started_at >= NOW() - INTERVAL '21 days'
     GROUP BY venue_slug
)
SELECT
    v.slug                       AS venue_slug,
    v.name                       AS venue_name,
    l.status                     AS latest_status,
    l.shows_found                AS latest_found,
    COALESCE(b.median_found, 0)  AS median_found,
    COALESCE(b.max_found, 0)     AS max_found,
    l.finished_at                AS last_finished_at,
    CASE
        WHEN l.venue_slug IS NULL
          OR l.finished_at IS NULL
          OR l.finished_at < NOW() - INTERVAL '30 hours'  THEN 'stale'
        WHEN l.status = 'failed'                           THEN 'failed'
        WHEN l.status IN ('success', 'partial')
         AND l.shows_found = 0
         AND COALESCE(b.max_found, 0) >= 1                 THEN 'silent-zero'
        WHEN l.status IN ('success', 'partial')
         AND COALESCE(b.median_found, 0) >= 5
         AND l.shows_found < 0.3 * b.median_found          THEN 'collapse'
        ELSE NULL
    END                          AS reason
  FROM venues v
  LEFT JOIN latest   l ON l.venue_slug = v.slug
  LEFT JOIN baseline b ON b.venue_slug = v.slug
 WHERE v.active;

COMMIT;
