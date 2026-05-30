-- venue_health: per-venue scrape health derived from scrape_runs.
--
-- The daily smoke test only checks the GLOBAL show total (> 100). A single
-- venue whose adapter silently starts returning 0 shows after a site redesign
-- still records status='success', shows_found=0 — and slips past unnoticed.
-- This view is the single source of truth for "which venues look broken",
-- read by both `scrape health` (Python CLI / CI) and the admin dashboard.
--
-- `reason` is NULL for healthy venues; consumers filter `WHERE reason IS NOT NULL`.
--   failed       — latest run raised (status='failed')
--   silent-zero  — latest success/partial found 0, but the venue HAS returned
--                  >=1 show within the 21-day baseline (i.e. it used to work)
--   collapse     — latest found < 30% of the 21-day median (baseline median >=5)
--   stale        — no run in 30h, or never scraped at all
--
-- Thresholds are intentionally baked in here so there is one source of truth;
-- tune them with a follow-up migration rather than per-consumer flags.

BEGIN;

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
  LEFT JOIN baseline b ON b.venue_slug = v.slug;

COMMIT;
