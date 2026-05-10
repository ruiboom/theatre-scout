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

export type VenueCategory = 'major' | 'mid' | 'fringe' | 'outer';

export interface VenueSummary {
  id: string;
  slug: string;
  name: string;
  /** scout's `area` (e.g. "Islington"). */
  neighbourhood: string;
  /** Optional tube/rail station, e.g. "Old Street". */
  nearest_tube: string | null;
  /** Tier in the four-bucket taxonomy used by the rails view. */
  category: VenueCategory;
}

export interface Venue extends VenueSummary {
  description: string;
  capacity: number | null;
  address: string;
  /** First half of UK postcode, e.g. "N1". Useful for area filters. */
  postcode_prefix: string | null;
  lat: number | null;
  lng: number | null;
  website: string;
  current_shows_count: number;
}

export interface Show {
  id: string;
  slug: string;
  title: string;
  show_type: ShowType;
  venue: VenueSummary;
  description_short: string;
  genres: string[];
  tags: string[];
  /** GBP, integer pounds. Stored as pence in the DB; converted at the API boundary. */
  price_min: number | null;
  price_max: number | null;
  /**
   * Run start / end. Most listings expose a date range rather than per-night times,
   * so these are the canonical dates for "what's playing" queries when there are
   * no individual performance rows.
   */
  start_date: string | null;
  end_date: string | null;
  /** ISO 8601 timestamp of the next individual performance, or null. */
  next_performance: string | null;
  /** Count of upcoming individual performances. 0 when only the date range is known. */
  performance_count: number;
  /** Hero image (generally extracted from the detail page during enrich). */
  image_url: string | null;
  duration_minutes: number | null;
  age_rating: string | null;
  content_warnings: string[];
  /** Canonical link to the venue's show / booking page. Listed shows always link out. */
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
