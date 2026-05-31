'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useRef } from 'react';

/**
 * Client-side visit beacon.
 *
 * Public pages are now CDN-cached (ISR), so the old server-side `trackEvent`
 * on render only fired when a page regenerated — not per visit. This posts one
 * `visit` event per client navigation instead. Two happy side-effects:
 *   1. non-JS crawlers (most of them) never run this, so they no longer inflate
 *      the events table or pin the Neon endpoint awake; and
 *   2. visit counts now reflect real browsers rather than bot traffic.
 * The `/api/v1/events` handler still drops any UA that looks like a bot.
 */
export function VisitBeacon() {
  const pathname = usePathname();
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!pathname || last.current === pathname) return;
    last.current = pathname;
    try {
      // keepalive lets the POST outlive a fast navigation away from the page.
      void fetch('/api/v1/events', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ type: 'visit', path: pathname }),
        keepalive: true,
      });
    } catch {
      /* analytics is best-effort — never let it surface to the user */
    }
  }, [pathname]);

  return null;
}
