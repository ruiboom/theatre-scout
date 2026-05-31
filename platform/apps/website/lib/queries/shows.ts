import { sql } from '../db';
import type { Show, ShowDetail, ShowType } from '@platform/shared';
import type { SearchShowsInput } from '@platform/shared';

/**
 * Pence (DB) → integer GBP (API).
 * The TOOL_SURFACE Show shape is GBP. Pence-precision stays in the DB and the
 * raw_data JSON for anyone who needs it.
 */
function penceToGbp(pence: number | null): number | null {
  return pence == null ? null : Math.round(pence / 100);
}

/** Hydrate a row into the canonical Show shape. */
type ShowRow = {
  id: string;
  slug: string;
  title: string;
  show_type: ShowType;
  description_short: string;
  price_min_pence: number | null;
  price_max_pence: number | null;
  start_date: string | null;
  end_date: string | null;
  duration_minutes: number | null;
  age_rating: string | null;
  content_warnings: string[];
  image_url: string | null;
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
  venue_category: 'major' | 'mid' | 'fringe' | 'outer';
};

function rowToShow(r: ShowRow): Show {
  return {
    id: r.id,
    slug: r.slug,
    title: r.title,
    show_type: r.show_type,
    venue: {
      id: r.venue_id,
      slug: r.venue_slug,
      name: r.venue_name,
      neighbourhood: r.venue_neighbourhood,
      nearest_tube: r.venue_nearest_tube,
      category: r.venue_category,
    },
    description_short: r.description_short,
    genres: r.genres ?? [],
    tags: r.tags ?? [],
    price_min: penceToGbp(r.price_min_pence),
    price_max: penceToGbp(r.price_max_pence),
    start_date: r.start_date,
    end_date: r.end_date,
    next_performance: r.next_performance ?? r.start_date,
    performance_count: Number(r.performance_count) || 0,
    image_url: r.image_url,
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
  s.show_type,
  s.description_short,
  s.price_min_pence,
  s.price_max_pence,
  s.start_date,
  s.end_date,
  s.duration_minutes,
  s.age_rating,
  s.content_warnings,
  s.image_url,
  s.booking_url,
  v.id   AS venue_id,
  v.slug AS venue_slug,
  v.name AS venue_name,
  v.neighbourhood AS venue_neighbourhood,
  v.nearest_tube  AS venue_nearest_tube,
  v.category      AS venue_category,
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
 *
 * The "is the show running on date X" check looks at BOTH `performances` (when
 * the venue exposes per-night times) AND the show's `start_date`/`end_date`
 * range (when only a run window is known). Most listings only give a range —
 * scout's adapters write start/end and skip performances entirely — so the
 * fallback path is the common case.
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

  // Prefer per-show performances when present; fall back to start_date/end_date
  // range overlap. The two sources are complementary, never contradictory.
  //
  // A show with no dates at all (scout adapters that fail to extract them)
  // gets included rather than filtered — better to surface a show with
  // missing timing than to hide it. A "When?" gap is more useful than a
  // false negative.
  const dateOverlap = sql`
    (
      EXISTS (
        SELECT 1 FROM performances p
         WHERE p.show_id = s.id
           AND p.starts_at::date BETWEEN ${dateFrom}::date AND ${dateTo}::date
      )
      OR (
        s.start_date IS NOT NULL
        AND s.start_date <= ${dateTo}::date
        AND (s.end_date IS NULL OR s.end_date >= ${dateFrom}::date)
      )
      OR s.start_date IS NULL
    )
  `;

  const filters = sql`
    ${dateOverlap}
    ${input.neighbourhood ? sql`AND v.neighbourhood ILIKE ${input.neighbourhood}` : sql``}
    ${input.category ? sql`AND v.category = ${input.category}` : sql``}
    ${input.show_type ? sql`AND s.show_type = ${input.show_type}` : sql``}
    ${
      input.q
        ? sql`AND (
            s.search_tsv @@ websearch_to_tsquery('english', ${input.q})
            OR v.name ILIKE '%' || ${input.q} || '%'
          )`
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
    ${
      input.first_seen_within_days != null
        ? sql`AND s.first_seen_at >= NOW() - (${input.first_seen_within_days} || ' days')::interval`
        : sql``
    }
    ${
      input.closing_within_days != null
        ? sql`AND s.end_date IS NOT NULL
              AND s.end_date >= ${dateFrom}::date
              AND s.end_date <= ${dateFrom}::date + (${input.closing_within_days} || ' days')::interval`
        : sql``
    }
  `;

  const orderBy = orderByFor(input.sort, input.dir);

  const rows = (await sql<ShowRow[]>`
    SELECT ${showColumns}
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE ${filters}
     ORDER BY ${orderBy}
     LIMIT ${limit}
  `) as ShowRow[];

  const countRows = await sql<{ count: number }[]>`
    SELECT COUNT(*)::int AS count
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE ${filters}
  `;
  const total = countRows[0]?.count ?? 0;

  return { shows: rows.map(rowToShow), total };
}

/** Sort field → SQL ORDER BY clause. Mirrors scout's sort options. */
function orderByFor(
  field: SearchShowsInput['sort'],
  dir: SearchShowsInput['dir'],
) {
  const desc = dir === 'desc';
  const direction = desc ? sql`DESC NULLS LAST` : sql`ASC NULLS LAST`;
  switch (field) {
    case 'first_seen':
      return sql`s.first_seen_at ${direction}, LOWER(s.title)`;
    case 'title':
      return sql`LOWER(s.title) ${direction}`;
    case 'venue':
      return sql`LOWER(v.name) ${direction}`;
    case 'end_date':
      return sql`s.end_date ${direction}, LOWER(s.title)`;
    case 'start_date':
    default:
      return sql`COALESCE(
        (SELECT MIN(p.starts_at)::date FROM performances p
          WHERE p.show_id = s.id AND p.starts_at >= NOW()),
        s.start_date
      ) ${direction}, LOWER(s.title)`;
  }
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

/**
 * openingsByDay — how many shows *open* (start their run) on each date in
 * [from, to]. Powers the /shows calendar grid's per-day "openings" highlight.
 *
 * Counting openings rather than "running on that day" is deliberate: most shows
 * carry only a start/end range, so a run-overlap count would mark nearly every
 * cell and tell the user nothing. An opening is a sparse, meaningful signal.
 *
 * Honours the same category/show_type/q filters as `searchShows` so the grid
 * stays consistent with the rest of the filter bar. Returns one row per day that
 * has at least one opening; days with none are simply absent.
 */
export async function openingsByDay(
  from: string,
  to: string,
  filters: Pick<SearchShowsInput, 'category' | 'show_type' | 'q'> = {},
): Promise<Array<{ day: string; count: number }>> {
  const rows = (await sql<{ day: string; count: number }[]>`
    SELECT to_char(s.start_date, 'YYYY-MM-DD') AS day, COUNT(*)::int AS count
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE s.start_date BETWEEN ${from}::date AND ${to}::date
       ${filters.category ? sql`AND v.category = ${filters.category}` : sql``}
       ${filters.show_type ? sql`AND s.show_type = ${filters.show_type}` : sql``}
       ${
         filters.q
           ? sql`AND (
               s.search_tsv @@ websearch_to_tsquery('english', ${filters.q})
               OR v.name ILIKE '%' || ${filters.q} || '%'
             )`
           : sql``
       }
     GROUP BY s.start_date
     ORDER BY s.start_date
  `) as Array<{ day: string; count: number }>;
  return rows.map((r) => ({ day: r.day, count: Number(r.count) || 0 }));
}

/**
 * recentlyAdded — shows first seen within the last `days`, newest first. Powers
 * the "Just Announced" editorial page; carries `first_seen_at` for the
 * "added Nd ago" badge. Excludes runs that have already ended.
 */
export async function recentlyAdded(
  days: number,
  limit: number,
): Promise<Array<Show & { first_seen_at: string }>> {
  const todayIso = new Date().toISOString().slice(0, 10);
  const rows = (await sql<(ShowRow & { first_seen_at: string })[]>`
    SELECT ${showColumns}, s.first_seen_at
      FROM shows s
      JOIN venues v ON v.id = s.venue_id
     WHERE s.first_seen_at >= NOW() - (${days} || ' days')::interval
       AND (s.end_date IS NULL OR s.end_date >= ${todayIso}::date)
     ORDER BY s.first_seen_at DESC, LOWER(s.title)
     LIMIT ${limit}
  `) as Array<ShowRow & { first_seen_at: string }>;
  return rows.map((r) => ({ ...rowToShow(r), first_seen_at: r.first_seen_at }));
}

/**
 * closingSoon — shows whose run ends within the next `days`, soonest first.
 * Powers the "Closing Soon" editorial page. `end_date` is on the Show, so the
 * "closes in N days" countdown is derived client-side.
 */
export async function closingSoon(days: number, limit: number): Promise<Show[]> {
  const todayIso = new Date().toISOString().slice(0, 10);
  const toIso = new Date(Date.now() + days * 86400_000)
    .toISOString()
    .slice(0, 10);
  const { shows } = await searchShows({
    date_from: todayIso,
    date_to: toIso,
    closing_within_days: days,
    sort: 'end_date',
    dir: 'asc',
    min_price: 0,
    limit,
  });
  return shows;
}

/**
 * Slug + last-modified for every current/upcoming show, for the XML sitemap.
 * Deliberately lean — no joins, no hydration — so generating the sitemap is one
 * cheap scan. Past shows are dropped (their detail pages 404 once pruned).
 */
export async function sitemapShows(): Promise<
  Array<{ slug: string; updated_at: string }>
> {
  return (await sql<{ slug: string; updated_at: string }[]>`
    SELECT slug, updated_at
      FROM shows
     WHERE start_date IS NULL OR end_date IS NULL OR end_date >= CURRENT_DATE
     ORDER BY updated_at DESC
     LIMIT 5000
  `) as Array<{ slug: string; updated_at: string }>;
}
