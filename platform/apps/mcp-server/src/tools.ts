import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { ApiClient } from './api-client.js';

/**
 * MCP tool definitions.
 *
 * Each tool's schema is the public-facing definition; the API in
 * @platform/shared/schemas is the canonical implementation. They MUST stay in
 * sync — there's an `assertSchemasMatch()` test in the website app that
 * fails CI if they drift.
 *
 * The `description` strings here are read by the AI to decide when to call
 * each tool, so write them like documentation for the model.
 */

// ---- shared sub-schemas ----
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const NearLatLng = z.object({
  lat: z.number(),
  lng: z.number(),
  radius_km: z.number().optional().default(2),
});

export function registerTools(server: McpServer, api: ApiClient) {
  // ---- search_shows --------------------------------------------------------
  server.tool(
    'search_shows',
    `Flexible search across all listings. The workhorse — use whenever the user
provides any combination of date, location, price, or genre filter.

Defaults: today through next week, 20 results, sorted by next performance date.
Returns { shows: Show[], total }. Empty result is { shows: [], total: 0 } —
never null.`,
    {
      date_from: isoDate.optional(),
      date_to: isoDate.optional(),
      neighbourhood: z.string().optional(),
      near: NearLatLng.optional(),
      max_price: z.number().nonnegative().optional(),
      min_price: z.number().nonnegative().optional(),
      genres: z.array(z.string()).optional(),
      tags: z.array(z.string()).optional(),
      venue_ids: z.array(z.string()).optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
    async (args) => json(await api.searchShows(args)),
  );

  // ---- get_show ------------------------------------------------------------
  server.tool(
    'get_show',
    `Full detail for a single show: long description, all upcoming
performances, creators (writer/director/cast), content warnings, reviews
summary. Use after a search result, or when the user asks about a specific
show by name.

Pass exactly one of show_id (UUID) or slug.`,
    {
      show_id: z.string().uuid().optional(),
      slug: z.string().optional(),
    },
    async (args) => {
      if (!args.show_id && !args.slug) {
        return error('Provide show_id or slug.');
      }
      return json(await api.getShow(args));
    },
  );

  // ---- whats_on ------------------------------------------------------------
  server.tool(
    'whats_on',
    `Convenience tool for the most common AI question: "what's on tonight /
this weekend?". Resolves a named time window in Europe/London and returns
matching shows.

Returns { shows, total, window: { from, to } } so you can confirm the
resolved dates back to the user ("Here's what's on this weekend, 12–14
September...").`,
    {
      when: z.enum([
        'tonight',
        'tomorrow',
        'this_weekend',
        'next_weekend',
        'this_week',
      ]),
      near: z
        .union([z.string(), z.object({ lat: z.number(), lng: z.number() })])
        .optional(),
      max_price: z.number().nonnegative().optional(),
    },
    async (args) => json(await api.whatsOn(args)),
  );

  // ---- recommend_shows ----------------------------------------------------
  server.tool(
    'recommend_shows',
    `Mood/vibe-based discovery. The "take a punt" tool — use when the user
asks for a recommendation by feel rather than exact filters.
Examples: "something weird", "a good first date show", "intense and
political", "make me laugh".

Returns { recommendations: [{ show, why }] }, where each 'why' is a 1–2
sentence rationale. Present them as curated picks, not a search result.`,
    {
      vibe: z.string().min(2),
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
      limit: z.number().int().min(1).max(20).optional(),
    },
    async (args) => json(await api.recommendShows(args)),
  );

  // ---- search_venues -------------------------------------------------------
  server.tool(
    'search_venues',
    `Find venues by name, area, or proximity. Use for questions like "what
venues are in Camden?", "where's the Bush Theatre?", or "pub theatres in
Stoke Newington".`,
    {
      query: z.string().optional(),
      neighbourhood: z.string().optional(),
      near: NearLatLng.optional(),
      limit: z.number().int().min(1).max(100).optional(),
    },
    async (args) => json(await api.searchVenues(args)),
  );

  // ---- get_venue -----------------------------------------------------------
  server.tool(
    'get_venue',
    `Full venue details, optionally with current programming. Use when the
user wants to know about a specific venue or asks "what's on at [venue]?".

Pass exactly one of venue_id (UUID) or slug. Set include_shows: false if you
only need venue metadata.`,
    {
      venue_id: z.string().uuid().optional(),
      slug: z.string().optional(),
      include_shows: z.boolean().optional(),
    },
    async (args) => {
      if (!args.venue_id && !args.slug) {
        return error('Provide venue_id or slug.');
      }
      return json(await api.getVenue(args));
    },
  );
}

// ---- helpers ----

function json(data: unknown) {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(data, null, 2) }],
  };
}

function error(message: string) {
  return {
    isError: true,
    content: [{ type: 'text' as const, text: message }],
  };
}
