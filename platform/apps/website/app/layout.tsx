import type { Metadata } from 'next';
import './globals.css';
import { lastScrapeAt } from '@/lib/queries/venues';
import { fmtRelative } from '@/lib/format';
import { Analytics } from '@vercel/analytics/next';
import { Suspense } from 'react';
import { unstable_cache } from 'next/cache';
import { SearchBeacon } from '@/components/visit-beacon';

// The layout renders on every dynamic request (/shows filters, /punt), and
// this one-row query was a Neon round trip each time. Cache it; the scrape
// workflow's revalidate call refreshes it the moment new data lands. The TTL
// must be >= the pages' own ISR TTL: Next takes the SMALLEST revalidate in the
// render tree as the route's, so a 10-minute value here would silently turn
// every 6-hour page into a 10-minute one.
const cachedLastScrapeAt = unstable_cache(lastScrapeAt, ['layout:last-scrape'], {
  revalidate: 21600,
  tags: ['shows'],
});

export const metadata: Metadata = {
  title: {
    default: 'Theatre Scout',
    template: '%s · Theatre Scout',
  },
  description:
    "London's other theatre scene. Pub theatres, fringe spaces, converted warehouses — where the interesting work happens.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // The bar shows when the DB was last refreshed. Tolerate a missing/empty DB
  // in dev so the page still renders without a working connection.
  let last: string | null = null;
  try {
    last = await cachedLastScrapeAt();
  } catch {
    last = null;
  }

  return (
    <html lang="en">
      <body>
        <header className="bar">
          <div className="bar-l">
            <a className="bar-tile" href="/" aria-label="Home">
              TS
            </a>
            <strong>TS</strong>
            <span className="bar-sep">/</span>
            <a href="/">Theatre Scout</a>
            <span className="bar-sep">/</span>
            <span>London</span>
          </div>
          <nav className="bar-r">
            <a href="/">Theatres</a>
            <span className="bar-sep">·</span>
            <a href="/shows">Shows</a>
            <span className="bar-sep bar-stat-extra">·</span>
            <span className="bar-actions">
              <span
                className="bar-stamp"
                title={last ? new Date(last).toLocaleString() : ''}
              >
                Last · {fmtRelative(last)}
              </span>
            </span>
          </nav>
        </header>
        <main className="page">{children}</main>
        <footer className="foot">
          <div>© Theatre Scout · London only · Daily index</div>
          <div>
            <a href="/faq">FAQ</a>
            <span className="bar-sep"> · </span>
            <a href="/about">About</a>
            <span className="bar-sep"> · </span>
            <a href="/privacy">Privacy</a>
            <span className="bar-sep"> · </span>
            <a href="/terms">Terms</a>
          </div>
        </footer>
        <Analytics />
        <Suspense fallback={null}>
          <SearchBeacon />
        </Suspense>
      </body>
    </html>
  );
}
