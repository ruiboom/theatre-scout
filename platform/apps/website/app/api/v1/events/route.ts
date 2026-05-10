import { NextResponse, type NextRequest } from 'next/server';
import { z } from 'zod';
import { eventMetaFromRequest, trackEvent } from '@/lib/track';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/events — record a single tracking event from the client.
 *
 * The website's own pages mostly track server-side from page renders, but
 * this endpoint covers the cases where you genuinely need a client-side
 * signal (e.g. an in-page interaction that doesn't navigate).
 *
 * Validation is permissive — events are best-effort.
 */
const Input = z.object({
  type: z.enum(['visit', 'search', 'outbound']),
  path: z.string().max(500).optional(),
  target: z.string().max(200).optional(),
  query: z.string().max(500).optional(),
});

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const parsed = Input.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: { code: 'invalid_input', message: 'Bad event payload.' } },
      { status: 400 },
    );
  }
  const meta = eventMetaFromRequest(req);
  await trackEvent({ ...parsed.data, ...meta });
  return NextResponse.json({ ok: true });
}
