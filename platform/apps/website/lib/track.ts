/**
 * Server-side analytics tracker. Fire-and-forget DB inserts into the events
 * table so the admin dashboard can show visit counts, top searches, and
 * outbound clicks without us depending on Vercel Analytics or a third party.
 *
 * Best-effort: a failed insert never breaks page rendering.
 */

import { sql } from './db';
import type { NextRequest } from 'next/server';

export type EventType = 'visit' | 'search' | 'outbound';

export interface TrackInput {
  type: EventType;
  path?: string | null;
  target?: string | null;
  query?: string | null;
  ua?: string | null;
  ip_prefix?: string | null;
}

/**
 * Insert a single event. Returns void; callers should NOT await unless they
 * need to ensure the row is persisted (rare).
 *
 * Errors are swallowed and logged. The dashboard is best-effort, not
 * source-of-truth — losing a few rows on a glitchy DB connection is fine.
 */
export async function trackEvent(input: TrackInput): Promise<void> {
  try {
    await sql`
      INSERT INTO events (type, path, target, query, ua, ip_prefix)
      VALUES (
        ${input.type},
        ${input.path ?? null},
        ${input.target ?? null},
        ${input.query ?? null},
        ${input.ua ?? null},
        ${input.ip_prefix ?? null}
      )
    `;
  } catch (err) {
    console.warn('trackEvent failed:', (err as Error).message);
  }
}

/**
 * Pull just the headers we want to record off a request. Storing only the
 * /24-style IP prefix (or the country header on Vercel) keeps us out of
 * "personal data" territory while still letting us spot bot floods.
 */
export function eventMetaFromRequest(req: NextRequest | Request): {
  ua: string | null;
  ip_prefix: string | null;
} {
  const headers =
    req instanceof Request ? req.headers : (req as NextRequest).headers;
  const ua = headers.get('user-agent');
  const ip =
    headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    headers.get('x-real-ip') ??
    null;
  // Truncate to /24 (or the first 3 IPv6 groups) — enough to identify a
  // crawler bot subnet but not an individual user.
  const ip_prefix = ip
    ? ip.includes(':')
      ? ip.split(':').slice(0, 3).join(':')
      : ip.split('.').slice(0, 3).join('.')
    : null;
  return { ua: ua ? ua.slice(0, 200) : null, ip_prefix };
}

/**
 * Build the tracked redirect URL used for outbound show clicks.
 * `<a href={trackedExternalHref(slug, booking_url)} target="_blank">…</a>`
 * routes through `/r` which records the event then 302s to `to`.
 */
export function trackedExternalHref(target: string, to: string): string {
  const params = new URLSearchParams({ type: 'outbound', target, to });
  return `/r?${params.toString()}`;
}
