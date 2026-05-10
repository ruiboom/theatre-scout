import { NextResponse, type NextRequest } from 'next/server';
import { eventMetaFromRequest, trackEvent } from '@/lib/track';

export const dynamic = 'force-dynamic';

/**
 * GET /r?type=outbound&target=<slug>&to=<url>
 *
 * Tracked-redirect endpoint for outbound clicks. The /shows row title
 * (which links to a venue's external booking page) routes through here so
 * we can record an `outbound` event before the 302.
 *
 * Defensive against open-redirect abuse: only http/https URLs are forwarded.
 * Bad inputs 302 to "/" rather than blowing up.
 */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const to = url.searchParams.get('to') ?? '';
  const target = url.searchParams.get('target') ?? null;
  const type = url.searchParams.get('type') ?? 'outbound';

  let dest: URL | null = null;
  try {
    dest = new URL(to);
    if (dest.protocol !== 'http:' && dest.protocol !== 'https:') dest = null;
  } catch {
    dest = null;
  }

  // Fire-and-forget the event before redirecting so a slow DB doesn't block
  // the user. Type narrows: 'outbound' is the only sensible value here.
  if (type === 'outbound') {
    const meta = eventMetaFromRequest(req);
    void trackEvent({ type: 'outbound', target, ...meta });
  }

  return NextResponse.redirect(dest ?? new URL('/', req.url), 302);
}
