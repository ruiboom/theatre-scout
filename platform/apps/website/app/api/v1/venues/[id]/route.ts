import { NextResponse, type NextRequest } from 'next/server';
import { getVenue } from '@/lib/queries/venues';
import { API_CACHE_CONTROL, jsonError } from '@/lib/api';

export const dynamic = 'force-dynamic';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const url = new URL(req.url);
  const includeShows = url.searchParams.get('include_shows') !== 'false';
  const isUuid = UUID_RE.test(id);

  const venue = await getVenue({
    ...(isUuid ? { venue_id: id } : { slug: id }),
    include_shows: includeShows,
  });
  if (!venue) return jsonError(404, 'not_found', `No venue matched ${id}`);
  return NextResponse.json(venue, {
    headers: { 'cache-control': API_CACHE_CONTROL },
  });
}
