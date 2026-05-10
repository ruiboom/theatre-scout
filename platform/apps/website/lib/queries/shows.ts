import { sql } from '../db';
import type { Show, ShowDetail } from '@platform/shared';
import type { SearchShowsInput } from '@platform/shared';

/**
 * Pence (DB) → integer GBP (API).
 * The TOOL_SURFACE Show shape is GBP. Pence-precision stays in the DB and the
 * raw_data JSON for anyone who needs it.
 */
function penceToGbp(pence: number | null): number {
  return pence == null ? 0 : Math.round(pence / 100);
}

/** Hydrate a row into the canonical Show shape. */
type ShowRow = {
  id: string;
  slug: string;
  title: string;
  description_short: string;
  price_min_pence: number | null;
  price_max_pence: number | null;
  duration_minutes: number | null;
  age_rating: string | null;
  content_warnings: string[];
  booking_url: string;
  next_performance: string | null;
  performance_count: number;
  genres: string[] | null;
  tags: string[] | null;
  venue_id: string;
  venue_slug: string;
  venue_name: string;
  venue_neighbourhood: string;
  venue_nearest_tube: string | null;
};

function rowToShow(r: ShowRow): Show {
  return {
    id: r.id,
    slug: r.slug,
    title: r.title,
    venue: {
      id: r.venue_id,
      slug: r.venue_slug,
      name: r.venue_name,
      neighbourhood: r.venue_neighbourhood,
      nearest_tube: r.venue_nearest_tube,
    },
    description_short: r.description_short,
    genres: r.genres ?? [],
    tags: r.tags ?? [],
    price_min: penceToGbp(r.price_min_pence),
    price_max: penceToGbp(r.price_max_pence),
    next_performance: r.next_performance,
    performance_count: Number(r.performance_count) || 0,
    duration_minutes: r.duration_minutes,
    age_rating: r.age_rating,
    content_warnings: r.content_warnings ?? [],
    booking_url: r.booking_url,
  };
}

/**
 * Reusable column projection that produces a Show row in one shot.
 * Keeping it in one place keeps every query that returns a Show identical.
 */
const showColumns = sql`
  s.id,
  s.slug,
  s.title,
  s.description_short,
  s.price_min_pence,
  s.price_max_pence,
  s.duration_minutes,
  s.age_rating,
  s.content_warnings,
  s.booking_url,
  v.id   AS venue_id,
  v.slug AS venue_slug,
  v.name AS venue_name,
  v.neighbourhood AS venue_neighbourhood,
  v.nearest_tube  AS venue_nearest_tube,
  (
    SELECT MIN(p.starts_at)
      FROM performances p
     WHERE p.show_id = s.id AND p.starts_at >= NOW()
  ) AS next_performance,
  (
    SELECT COUNT(*)
      FROM performances p
     WHERE p.show_id = s.id AND p.starts_at >= NOW()
  ) AS performance_count,
  (
    SELECT COALESCE(array_agg(t.slug ORDER BY t.slug) FILTER (WHERE t.type = 'genre'), '{}')
      FROM show_tags st JOIN tags t ON t.id = st.tag_id
     WHERE st.show_id = s.id AND t.type = 'genre'
  ) AS genres,
  (
    SELECT COALESCE(array_agg(t.slug ORDER BY t.slug) FILTER (WHERE t.type = 'tag'), '{}')
      FROM show_tags st JOIN tags t ON t.id = st.tag_id
     WHERE st.show_id = s.id AND t.type = 'tag'
  ) AS tags
`;

/**
 * search_shows — the workhorse. See TOOL_SURFACE.md.
 *
 * Defaults: this week (today → +7 days), date order, limit 20.
 * Empty result returns `{ shows: [], total: 0 }`, never null.
 */
export async function searchShows(
  input: SearchShowsInput,
): Promise<{ shows: Show[]; total: number }> {
  const dateFrom = input.date_from ?? new Date().toISOString().slice(0, 10);
  const dateTo =
    input.date_to ??
    new Date(Date.now() + 7 * 86400_000).toISOString().slice(0, 10);
  const limit = input.limit ?? 20;
  const minPrice = (input.min_price ?? 0) * 100;
  const maxPrice = input.max_price != null ? input.max_price * 100 : null;

  const filters = sql`
    EXISTS (
      SELECT 1 FROM performances p
       WHERE p.show_id = s.id
         AND p.starts_at::date BETWEEN ${dateFrom}::date AND ${dateTo}::date
    )
    ${input.neighbourhood ? sql`AND v.neighbourhood ILIKE ${input.neighbourhood}` : sql``}
    ${
      input.near
        ? sql`AND ST_DWithin(
            v.location,
            ST_MakePoint(${input.near.lng}, ${input.near.lat})::geography,
            ${input.near.radius_km * 1000}
          )`
        : sql``
    }
    ${
      maxPrice != null
        ? sql`AND COALESCE(s.price_min_pence, 0) <= ${maxPrice}`
        : sql``
    }
    AND COALESCE(s.price_max_pence, 0) >= ${minPrice}
    ${
      input.genres && input.genres.length > 0
        ? sql`AND EXISTS (
            SELECT 1 FROM show_tags st JOIN tags t ON t.id = st.tag_id
             WHERE st.show_id = s.id
               AND t.type = 'genre'
               AND t.slug = ANY(${input.genres})
          )`
        : sql``
    }
    ${
      input.tags && input.tags.length > 0
        ? sql`AND EXISTS (
            SELECT 1 FROM show_tags st JOIN tags t ON t.id = st.tag_id
             WHERE st.show_id = s.id
               AND t.type = 'tag'
               AND t.slug = ANY(${input.tags})
          )`
        : sql``
    }
    ${
      input.venue_ids && input.venue_ids.length > 0
        ? sql`AND s.venue_id = ANY(${input.venue_ids})`
        : sql``
    }
  `;

  const rows = (await sql<ShowRow[]>`
    SELECT ${showColumns}
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE ${filters}
     ORDER BY (
       SELECT MIN(p.starts_at) FROM performances p
        WHERE p.show_id = s.id AND p.starts_at >= NOW()
     ) NULLS LAST, s.title
     LIMIT ${limit}
  `) as ShowRow[];

  const [{ count }] = await sql<{ count: number }[]>`
    SELECT COUNT(*)::int AS count
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE ${filters}
  `;

  return { shows: rows.map(rowToShow), total: count };
}

/** get_show — full detail for a single show. */
export async function getShow(opts: {
  show_id?: string;
  slug?: string;
}): Promise<ShowDetail | null> {
  const rows = (await sql<(ShowRow & {
    description_full: string;
    writer: string | null;
    director: string | null;
    cast_members: string[];
    reviews_summary: string | null;
  })[]>`
    SELECT ${showColumns},
           s.description_full,
           s.writer,
           s.director,
           s.cast_members,
           s.reviews_summary
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE ${
       opts.show_id
         ? sql`s.id = ${opts.show_id}`
         : sql`LOWER(s.slug) = LOWER(${opts.slug!})`
     }
     LIMIT 1
  `) as Array<
    ShowRow & {
      description_full: string;
      writer: string | null;
      director: string | null;
      cast_members: string[];
      reviews_summary: string | null;
    }
  >;
  if (rows.length === 0) return null;
  const row = rows[0]!;

  const performances = await sql<
    {
      starts_at: string;
      available_tickets_estimate: number | null;
      sold_out: boolean;
    }[]
  >`
    SELECT starts_at, available_tickets_estimate, sold_out
      FROM performances
     WHERE show_id = ${row.id} AND starts_at >= NOW()
     ORDER BY starts_at
  `;

  const base = rowToShow(row);
  return {
    ...base,
    description_full: row.description_full,
    performances: performances.map((p) => ({
      datetime: p.starts_at,
      available_tickets_estimate: p.available_tickets_estimate,
      sold_out: p.sold_out,
    })),
    reviews_summary: row.reviews_summary,
    creators: {
      writer: row.writer,
      director: row.director,
      cast: row.cast_members ?? [],
    },
  };
}
