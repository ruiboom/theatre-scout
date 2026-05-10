import { NextResponse, type NextRequest } from 'next/server';
import { RecommendShowsInput } from '@platform/shared';
import { recommendShows } from '@/lib/recommend';
import { parseInput } from '@/lib/api';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/recommend — backs the `recommend_shows` MCP tool.
 *
 * Takes a vibe string + optional constraints. Returns shows ranked by
 * relevance to the vibe, each with a 1–2 sentence `why` generated server-side
 * (the magic that turns a search result into a recommendation).
 */
export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const parsed = await parseInput(RecommendShowsInput, body);
  if (!parsed.ok) return parsed.response;
  const result = await recommendShows(parsed.data);
  return NextResponse.json(result);
}
