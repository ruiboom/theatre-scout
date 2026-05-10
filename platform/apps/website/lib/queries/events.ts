import { sql } from '../db';

/**
 * Aggregate queries for the admin dashboard. Read-only — no side effects.
 *
 * All counts cover the configurable lookback window (default 7 days). The
 * dashboard renders 24h / 7d / 30d side-by-side via three calls.
 */

export interface VisitTotals {
  last_24h: number;
  last_7d: number;
  last_30d: number;
}

export async function visitTotals(): Promise<VisitTotals> {
  const rows = await sql<
    { last_24h: number; last_7d: number; last_30d: number }[]
  >`
    SELECT
      COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '24 hours')::int AS last_24h,
      COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '7 days')::int   AS last_7d,
      COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '30 days')::int  AS last_30d
    FROM events
    WHERE type = 'visit'
  `;
  return rows[0] ?? { last_24h: 0, last_7d: 0, last_30d: 0 };
}

export interface RankedRow {
  key: string;
  count: number;
}

/** Top searches in the last `days`. */
export async function topSearches(
  days: number,
  limit = 10,
): Promise<RankedRow[]> {
  const rows = await sql<{ key: string; count: number }[]>`
    SELECT lower(query) AS key, COUNT(*)::int AS count
      FROM events
     WHERE type = 'search'
       AND query IS NOT NULL AND length(query) > 0
       AND occurred_at >= NOW() - (${days} || ' days')::interval
     GROUP BY lower(query)
     ORDER BY count DESC, key ASC
     LIMIT ${limit}
  `;
  return rows;
}

/**
 * Top venue clicks — counted as visits to /venues/<slug>. Returns the
 * venue's display name when joinable, falling back to the slug.
 */
export async function topVenueClicks(
  days: number,
  limit = 10,
): Promise<Array<{ slug: string; name: string; count: number }>> {
  const rows = await sql<{ slug: string; name: string; count: number }[]>`
    SELECT
      slug,
      COALESCE(v.name, slug) AS name,
      count
    FROM (
      SELECT
        substring(path FROM '^/venues/([^/?#]+)') AS slug,
        COUNT(*)::int AS count
      FROM events
      WHERE type = 'visit'
        AND path LIKE '/venues/%'
        AND occurred_at >= NOW() - (${days} || ' days')::interval
      GROUP BY substring(path FROM '^/venues/([^/?#]+)')
    ) e
    LEFT JOIN venues v ON v.slug = e.slug
    WHERE e.slug IS NOT NULL
    ORDER BY count DESC, slug ASC
    LIMIT ${limit}
  `;
  return rows;
}

/**
 * Top outbound show clicks — events with type='outbound', target = show
 * slug. Returns the show's title where joinable.
 */
export async function topShowClicks(
  days: number,
  limit = 10,
): Promise<
  Array<{ slug: string; title: string; venue: string | null; count: number }>
> {
  const rows = await sql<
    { slug: string; title: string; venue: string | null; count: number }[]
  >`
    SELECT
      e.target AS slug,
      COALESCE(s.title, e.target) AS title,
      v.name AS venue,
      e.count::int
    FROM (
      SELECT target, COUNT(*) AS count
        FROM events
       WHERE type = 'outbound'
         AND target IS NOT NULL
         AND occurred_at >= NOW() - (${days} || ' days')::interval
       GROUP BY target
    ) e
    LEFT JOIN shows  s ON s.slug = e.target
    LEFT JOIN venues v ON v.id   = s.venue_id
    ORDER BY e.count DESC, e.target ASC
    LIMIT ${limit}
  `;
  return rows;
}

/** Most-recent scrape_run per venue, plus its overall stats. */
export interface ScrapeStatus {
  total_venues: number;
  successful_today: number;
  failed_today: number;
  last_run_at: string | null;
}
export async function scrapeStatus(): Promise<ScrapeStatus> {
  const rows = await sql<
    {
      total_venues: number;
      successful_today: number;
      failed_today: number;
      last_run_at: string | null;
    }[]
  >`
    SELECT
      (SELECT COUNT(*) FROM venues)::int AS total_venues,
      (SELECT COUNT(*) FROM scrape_runs
        WHERE status = 'success' AND finished_at >= NOW() - INTERVAL '36 hours')::int AS successful_today,
      (SELECT COUNT(*) FROM scrape_runs
        WHERE status = 'failed'  AND finished_at >= NOW() - INTERVAL '36 hours')::int AS failed_today,
      (SELECT MAX(finished_at) FROM scrape_runs WHERE status IN ('success', 'partial'))::text AS last_run_at
  `;
  return rows[0] ?? {
    total_venues: 0,
    successful_today: 0,
    failed_today: 0,
    last_run_at: null,
  };
}
