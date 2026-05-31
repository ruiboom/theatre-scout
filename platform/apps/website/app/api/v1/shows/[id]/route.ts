import { NextResponse, type NextRequest } from 'next/server';
import { getShow } from '@/lib/queries/shows';
import { API_CACHE_CONTROL, jsonError } from '@/lib/api';

export const dynamic = 'force-dynamic';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * GET /api/v1/shows/{id_or_slug} — backs the `get_show` MCP tool.
 *
 * The path segment is treated as an id when it's a UUID, otherwise as a slug.
 * This keeps routes flat (no `?slug=` switching) for cleaner OpenAPI export.
 */
export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const isUuid = UUID_RE.test(id);
  const show = await getShow(isUuid ? { show_id: id } : { slug: id });
  if (!show) return jsonError(404, 'not_found', `No show matched ${id}`);
  return NextResponse.json(show, {
    headers: { 'cache-control': API_CACHE_CONTROL },
  });
}
