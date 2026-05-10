import { NextResponse, type NextRequest } from 'next/server';
import { WhatsOnInput, type SearchShowsInput } from '@platform/shared';
import { searchShows } from '@/lib/queries/shows';
import { searchVenues } from '@/lib/queries/venues';
import { paramsFromUrl, parseInput } from '@/lib/api';
import { resolveWindow } from '@/lib/time';

export const dynamic = 'force-dynamic';

/**
 * GET /api/v1/whats-on — backs the `whats_on` MCP tool.
 *
 * Resolves a `when` enum into a Europe/London-aware date window, optionally
 * narrows by neighbourhood/coords, and reuses search_shows under the hood.
 */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const raw = paramsFromUrl(url);
  // The `near` param can come in as a string OR a JSON-encoded {lat,lng}.
  if (typeof raw.near === 'string' && raw.near.startsWith('{')) {
    try {
      raw.near = JSON.parse(raw.near);
    } catch {
      /* leave as string */
    }
  }
  const parsed = await parseInput(WhatsOnInput, raw);
  if (!parsed.ok) return parsed.response;

  const window = resolveWindow(parsed.data.when);

  const searchInput: SearchShowsInput = {
    date_from: window.from,
    date_to: window.to,
    max_price: parsed.data.max_price,
    limit: 20,
    min_price: 0,
  };

  if (typeof parsed.data.near === 'string') {
    // Resolve a neighbourhood / venue-name hint into a coord by looking up the
    // closest venue match. Imperfect, but matches user intent for "near
    // London Bridge" style prompts.
    const { venues } = await searchVenues({
      query: parsed.data.near,
      limit: 1,
    });
    const candidate = venues[0];
    if (candidate) searchInput.neighbourhood = candidate.neighbourhood;
  } else if (parsed.data.near) {
    searchInput.near = {
      lat: parsed.data.near.lat,
      lng: parsed.data.near.lng,
      radius_km: 2,
    };
  }

  const { shows, total } = await searchShows(searchInput);
  return NextResponse.json({ shows, total, window });
}
