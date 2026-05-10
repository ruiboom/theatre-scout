/**
 * Canonical types for the listings platform.
 *
 * These match `docs/TOOL_SURFACE.md` — they are the contract between the
 * Internal API and every surface (website, MCP server, custom GPT).
 *
 * If you change a shape here, update TOOL_SURFACE.md and the API in lockstep.
 */

export type ShowType =
  | 'play'
  | 'musical'
  | 'comedy'
  | 'dance'
  | 'opera'
  | 'family'
  | 'cabaret'
  | 'other';

export interface VenueSummary {
  id: string;
  slug: string;
  name: string;
  neighbourhood: string;
  nearest_tube: string | null;
}

export interface Venue extends VenueSummary {
  description: string;
  capacity: number | null;
  address: string;
  lat: number;
  lng: number;
  website: string;
  current_shows_count: number;
}

export interface Show {
  id: string;
  slug: string;
  title: string;
  venue: VenueSummary;
  description_short: string;
  genres: string[];
  tags: string[];
  /** GBP, integer pounds (the API also exposes pence-precision via the DB). */
  price_min: number;
  price_max: number;
  /** ISO 8601 timestamp, or null if no upcoming performance is on the books. */
  next_performance: string | null;
  performance_count: number;
  duration_minutes: number | null;
  age_rating: string | null;
  content_warnings: string[];
  booking_url: string;
}

export interface Performance {
  datetime: string;
  available_tickets_estimate: number | null;
  sold_out: boolean;
}

export interface ShowDetail extends Show {
  description_full: string;
  performances: Performance[];
  reviews_summary: string | null;
  creators: {
    writer: string | null;
    director: string | null;
    cast: string[];
  };
}

export interface VenueDetail extends Venue {
  current_shows: Show[];
}

export interface Recommendation {
  show: Show;
  /** Server-generated 1–2 sentence rationale. The reason this is an "AI-grade" tool. */
  why: string;
}

// ---- Tool envelope shapes (return types) ----

export interface SearchShowsResult {
  shows: Show[];
  total: number;
}

export interface WhatsOnResult {
  shows: Show[];
  total: number;
  window: { from: string; to: string };
}

export interface RecommendShowsResult {
  recommendations: Recommendation[];
}

export interface SearchVenuesResult {
  venues: VenueSummary[];
  total: number;
}

// ---- Error envelope ----

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
