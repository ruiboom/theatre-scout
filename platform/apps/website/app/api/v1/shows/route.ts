import { NextResponse, type NextRequest } from 'next/server';
import { SearchShowsInput } from '@platform/shared';
import { searchShows } from '@/lib/queries/shows';
import { paramsFromUrl, parseInput } from '@/lib/api';

export const dynamic = 'force-dynamic';

/**
 * GET /api/v1/shows — backs the `search_shows` MCP tool.
 *
 * Accepts the SearchShowsInput zod schema as URL query params. Repeated keys
 * become arrays (`?genres=comedy&genres=experimental`).
 */
export async function GET(req: NextRequest) {
  const parsed = await parseInput(
    SearchShowsInput,
    paramsFromUrl(new URL(req.url)),
  );
  if (!parsed.ok) return parsed.response;
  const result = await searchShows(parsed.data);
  return NextResponse.json(result);
}
