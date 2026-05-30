/**
 * Zod schemas for the tool surface.
 *
 * Use these to validate inputs at the API boundary and to derive MCP tool
 * input definitions. The schemas ARE the input contract — TOOL_SURFACE.md
 * is the human-readable mirror.
 */

import { z } from 'zod';

// ---- Primitives ----

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'expected ISO date (YYYY-MM-DD)');

const slug = z
  .string()
  .min(1)
  .max(120)
  .regex(/^[a-z0-9-]+$/, 'lowercase, digits, hyphens only');

const id = z.string().uuid();

const NearLatLng = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
  radius_km: z.number().positive().max(50).optional().default(2),
});

// ---- search_shows ----

const ShowTypeEnum = z.enum([
  'play',
  'musical',
  'comedy',
  'dance',
  'opera',
  'family',
  'cabaret',
  'other',
]);

const VenueCategoryEnum = z.enum(['major', 'mid', 'fringe', 'outer']);

const WhenChip = z.enum(['today', 'week', 'new', 'closing']);

export const SearchShowsInput = z.object({
  date_from: isoDate.optional(),
  date_to: isoDate.optional(),
  neighbourhood: z.string().min(1).max(64).optional(),
  near: NearLatLng.optional(),
  max_price: z.number().nonnegative().optional(),
  min_price: z.number().nonnegative().optional().default(0),
  genres: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  venue_ids: z.array(id).optional(),
  /** Filter by venue tier — surfaces the rails-view category filter. */
  category: VenueCategoryEnum.optional(),
  /** Filter by show type — heuristic-classified at scrape time. */
  show_type: ShowTypeEnum.optional(),
  /** Web UI chip: "today" / "week" / "new" / "closing". Resolves server-side. */
  when: WhenChip.optional(),
  /** Only shows first seen within the last N days — powers "Just Announced". */
  first_seen_within_days: z.number().int().min(1).max(365).optional(),
  /** Only shows whose run ends within the next N days — powers "Closing Soon". */
  closing_within_days: z.number().int().min(1).max(365).optional(),
  /** Free-text title search. */
  q: z.string().min(1).max(200).optional(),
  /** Sort field for the list view. */
  sort: z.enum(['start_date', 'end_date', 'title', 'venue', 'first_seen']).optional(),
  /** Sort direction. */
  dir: z.enum(['asc', 'desc']).optional(),
  limit: z.number().int().min(1).max(200).optional().default(20),
});
export type SearchShowsInput = z.infer<typeof SearchShowsInput>;

// ---- get_show ----

export const GetShowInput = z
  .object({
    show_id: id.optional(),
    slug: slug.optional(),
  })
  .refine(
    (v) => !!v.show_id !== !!v.slug,
    'exactly one of show_id or slug is required',
  );
export type GetShowInput = z.infer<typeof GetShowInput>;

// ---- whats_on ----

export const WhatsOnInput = z.object({
  when: z.enum([
    'tonight',
    'tomorrow',
    'this_weekend',
    'next_weekend',
    'this_week',
  ]),
  near: z
    .union([
      z.string(),
      z.object({ lat: z.number(), lng: z.number() }),
    ])
    .optional(),
  max_price: z.number().nonnegative().optional(),
});
export type WhatsOnInput = z.infer<typeof WhatsOnInput>;

// ---- recommend_shows ----

export const RecommendShowsInput = z.object({
  vibe: z.string().min(2).max(500),
  constraints: z
    .object({
      date_from: isoDate.optional(),
      date_to: isoDate.optional(),
      max_price: z.number().nonnegative().optional(),
      neighbourhood: z.string().optional(),
      near: NearLatLng.optional(),
    })
    .optional(),
  exclude_genres: z.array(z.string()).optional(),
  limit: z.number().int().min(1).max(20).optional().default(5),
});
export type RecommendShowsInput = z.infer<typeof RecommendShowsInput>;

// ---- search_venues ----

export const SearchVenuesInput = z.object({
  query: z.string().min(1).max(120).optional(),
  neighbourhood: z.string().min(1).max(64).optional(),
  near: NearLatLng.optional(),
  limit: z.number().int().min(1).max(100).optional().default(20),
});
export type SearchVenuesInput = z.infer<typeof SearchVenuesInput>;

// ---- get_venue ----

export const GetVenueInput = z
  .object({
    venue_id: id.optional(),
    slug: slug.optional(),
    include_shows: z.boolean().optional().default(true),
  })
  .refine(
    (v) => !!v.venue_id !== !!v.slug,
    'exactly one of venue_id or slug is required',
  );
export type GetVenueInput = z.infer<typeof GetVenueInput>;
