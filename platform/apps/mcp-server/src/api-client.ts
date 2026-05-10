import type {
  RecommendShowsResult,
  SearchShowsResult,
  SearchVenuesResult,
  ShowDetail,
  VenueDetail,
  WhatsOnResult,
} from '@platform/shared';
import type {
  GetShowInput,
  GetVenueInput,
  RecommendShowsInput,
  SearchShowsInput,
  SearchVenuesInput,
  WhatsOnInput,
} from '@platform/shared';

/**
 * Fetch wrapper for the Internal API. Every MCP tool ends here.
 *
 * Construct one per request — workers don't share state across invocations
 * unless we want them to.
 */
export class ApiClient {
  constructor(private baseUrl: string) {}

  async searchShows(input: SearchShowsInput): Promise<SearchShowsResult> {
    return this.get('/shows', flatten(input));
  }

  async getShow(input: GetShowInput): Promise<ShowDetail> {
    const ident = input.show_id ?? input.slug;
    return this.get(`/shows/${encodeURIComponent(ident!)}`);
  }

  async whatsOn(input: WhatsOnInput): Promise<WhatsOnResult> {
    const params: Record<string, string | number | undefined> = {
      when: input.when,
      max_price: input.max_price,
    };
    if (typeof input.near === 'string') {
      params.near = input.near;
    } else if (input.near) {
      params.near = JSON.stringify(input.near);
    }
    return this.get('/whats-on', params);
  }

  async recommendShows(
    input: RecommendShowsInput,
  ): Promise<RecommendShowsResult> {
    // Strip nulls recursively. The MCP tool schemas accept null for unspecified
    // optionals (Claude's convention) but the Internal API's shared zod schemas
    // use plain `.optional()` and would reject null. Keep the wire format clean.
    return this.post('/recommend', stripNulls(input));
  }

  async searchVenues(input: SearchVenuesInput): Promise<SearchVenuesResult> {
    return this.get('/venues', flatten(input));
  }

  async getVenue(input: GetVenueInput): Promise<VenueDetail> {
    const ident = input.venue_id ?? input.slug;
    const qs = input.include_shows === false ? '?include_shows=false' : '';
    return this.get(`/venues/${encodeURIComponent(ident!)}${qs}`);
  }

  // ---- internals ----

  private async get<T>(
    path: string,
    params: Record<string, unknown> = {},
  ): Promise<T> {
    const url = new URL(this.baseUrl + path);
    for (const [k, v] of Object.entries(params)) {
      if (v == null) continue;
      if (Array.isArray(v)) {
        for (const item of v) url.searchParams.append(k, String(item));
      } else if (typeof v === 'object') {
        url.searchParams.set(k, JSON.stringify(v));
      } else {
        url.searchParams.set(k, String(v));
      }
    }
    const res = await fetch(url, {
      headers: { accept: 'application/json' },
    });
    if (!res.ok) {
      throw new Error(
        `Internal API ${res.status} ${res.statusText} for ${url.pathname}`,
      );
    }
    return (await res.json()) as T;
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(this.baseUrl + path, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(
        `Internal API ${res.status} ${res.statusText} for POST ${path}`,
      );
    }
    return (await res.json()) as T;
  }
}

function flatten(o: object): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) {
    if (v != null) out[k] = v;
  }
  return out;
}

/**
 * Recursive null-stripper for POST bodies. The MCP tool schemas accept null
 * for unspecified optionals (matches Claude's convention) but the website's
 * shared schemas use plain `.optional()` and would 400 on null. Strip
 * everywhere before serialising.
 */
function stripNulls<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map(stripNulls) as unknown as T;
  }
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      if (v === null || v === undefined) continue;
      out[k] = stripNulls(v);
    }
    return out as T;
  }
  return value;
}
