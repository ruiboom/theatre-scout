import { sql } from '../db';
import type {
  Venue,
  VenueCategory,
  VenueDetail,
  VenueSummary,
} from '@platform/shared';
import type { SearchVenuesInput } from '@platform/shared';
import { searchShows } from './shows';

type VenueRow = {
  id: string;
  slug: string;
  name: string;
  neighbourhood: string;
  nearest_tube: string | null;
  category: VenueCategory;
};

function rowToSummary(r: VenueRow): VenueSummary {
  return {
    id: r.id,
    slug: r.slug,
    name: r.name,
    neighbourhood: r.neighbourhood,
    nearest_tube: r.nearest_tube,
    category: r.category,
  };
}

export async function searchVenues(
  input: SearchVenuesInput,
): Promise<{ venues: VenueSummary[]; total: number }> {
  const limit = input.limit ?? 20;

  const filters = sql`
    1 = 1
    ${
      input.query
        ? sql`AND v.name ILIKE ${'%' + input.query + '%'}`
        : sql``
    }
    ${
      input.neighbourhood
        ? sql`AND v.neighbourhood ILIKE ${input.neighbourhood}`
        : sql``
    }
    ${
      input.near
        ? sql`AND ST_DWithin(
            v.location,
            ST_MakePoint(${input.near.lng}, ${input.near.lat})::geography,
            ${input.near.radius_km * 1000}
          )`
        : sql``
    }
  `;

  const rows = (await sql<VenueRow[]>`
    SELECT v.id, v.slug, v.name, v.neighbourhood, v.nearest_tube, v.category
      FROM venues v
     WHERE ${filters}
     ORDER BY v.name
     LIMIT ${limit}
  `) as VenueRow[];

  const [{ count }] = await sql<{ count: number }[]>`
    SELECT COUNT(*)::int AS count FROM venues v WHERE ${filters}
  `;

  return { venues: rows.map(rowToSummary), total: count };
}

/** Show-counts per venue, for the home-page index. */
export async function listVenuesWithCounts(): Promise<
  Array<VenueSummary & { show_count: number }>
> {
  type Row = VenueRow & { show_count: number };
  const rows = (await sql<Row[]>`
    SELECT v.id, v.slug, v.name, v.neighbourhood, v.nearest_tube, v.category,
           COALESCE(c.n, 0)::int AS show_count
      FROM venues v
      LEFT JOIN (
        SELECT venue_id, COUNT(*) AS n
          FROM shows s
         WHERE
           EXISTS (
             SELECT 1 FROM performances p
              WHERE p.show_id = s.id AND p.starts_at >= NOW()
           )
           OR (
             s.start_date IS NOT NULL
             AND (s.end_date IS NULL OR s.end_date >= CURRENT_DATE)
           )
         GROUP BY venue_id
      ) c ON c.venue_id = v.id
     ORDER BY LOWER(REGEXP_REPLACE(v.name, '^The +', '', 'i'))
  `) as Row[];
  return rows.map((r) => ({ ...rowToSummary(r), show_count: r.show_count }));
}

type VenueDetailRow = VenueRow & {
  description: string;
  capacity: number | null;
  address: string;
  postcode_prefix: string | null;
  lat: number | null;
  lng: number | null;
  website: string;
};

export async function getVenue(opts: {
  venue_id?: string;
  slug?: string;
  include_shows?: boolean;
}): Promise<VenueDetail | Venue | null> {
  const rows = (await sql<VenueDetailRow[]>`
    SELECT v.id, v.slug, v.name, v.neighbourhood, v.nearest_tube, v.category,
           v.description, v.capacity, v.address, v.postcode_prefix,
           ST_Y(v.location::geometry) AS lat,
           ST_X(v.location::geometry) AS lng,
           v.website
      FROM venues v
     WHERE ${
       opts.venue_id
         ? sql`v.id = ${opts.venue_id}`
         : sql`LOWER(v.slug) = LOWER(${opts.slug!})`
     }
     LIMIT 1
  `) as VenueDetailRow[];

  if (rows.length === 0) return null;
  const r = rows[0]!;

  // Count shows that are running today or have a future performance, mirroring
  // the date-overlap rule in searchShows so the count matches what the user sees.
  const [{ count: currentShowsCount }] = await sql<{ count: number }[]>`
    SELECT COUNT(DISTINCT s.id)::int AS count
      FROM shows s
     WHERE s.venue_id = ${r.id}
       AND (
         EXISTS (
           SELECT 1 FROM performances p
            WHERE p.show_id = s.id AND p.starts_at >= NOW()
         )
         OR (
           s.start_date IS NOT NULL
           AND (s.end_date IS NULL OR s.end_date >= CURRENT_DATE)
         )
       )
  `;

  const venue: Venue = {
    id: r.id,
    slug: r.slug,
    name: r.name,
    neighbourhood: r.neighbourhood,
    nearest_tube: r.nearest_tube,
    category: r.category,
    description: r.description,
    capacity: r.capacity,
    address: r.address,
    postcode_prefix: r.postcode_prefix,
    lat: r.lat,
    lng: r.lng,
    website: r.website,
    current_shows_count: currentShowsCount,
  };

  if (opts.include_shows) {
    const { shows } = await searchShows({
      venue_ids: [r.id],
      limit: 50,
      min_price: 0,
      // wide window — venue page wants the full programme
      date_from: new Date().toISOString().slice(0, 10),
      date_to: new Date(Date.now() + 365 * 86400_000).toISOString().slice(0, 10),
    });
    return { ...venue, current_shows: shows } satisfies VenueDetail;
  }

  return venue;
}

/** When was the most recent successful scrape across all venues? */
export async function lastScrapeAt(): Promise<string | null> {
  const rows = (await sql<{ finished_at: string | null }[]>`
    SELECT MAX(finished_at) AS finished_at
      FROM scrape_runs
     WHERE status IN ('success', 'partial')
  `) as { finished_at: string | null }[];
  return rows[0]?.finished_at ?? null;
}
