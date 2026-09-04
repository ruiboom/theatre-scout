'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';

/**
 * Client-side analytics beacon.
 *
 * Page views are Vercel Analytics' job (see `<Analytics />` in the layout).
 * This used to also POST a `visit` event per navigation into our own events
 * table — one function invocation plus one Neon INSERT per page view, which
 * both cost money and kept the Neon endpoint from ever autosuspending. That's
 * gone; only the signal Vercel Analytics can't give us is recorded here: the
 * free-text search term on /shows. Outbound clicks still go through `/r`.
 *
 * Because this reads the query string it must sit inside a <Suspense>
 * boundary (the layout does that) so it doesn't drag static pages into
 * client-side rendering.
 */
export function SearchBeacon() {
  const pathname = usePathname();
  const params = useSearchParams();
  const q = pathname === '/shows' ? (params.get('q') ?? '').trim() : '';
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!q || last.current === q) return;
    last.current = q;
    try {
      // keepalive lets the POST outlive a fast navigation away from the page.
      void fetch('/api/v1/events', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ type: 'search', query: q.slice(0, 500) }),
        keepalive: true,
      });
    } catch {
      /* analytics is best-effort — never let it surface to the user */
    }
  }, [q]);

  return null;
}
