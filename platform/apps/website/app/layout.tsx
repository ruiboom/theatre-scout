import type { Metadata } from 'next';
import './globals.css';
import { lastScrapeAt } from '@/lib/queries/venues';
import { fmtRelative } from '@/lib/format';

export const metadata: Metadata = {
  title: {
    default: 'Anywhere But The West End',
    template: '%s · Anywhere But The West End',
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
    last = await lastScrapeAt();
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
            <a href="/">Anywhere But The West End</a>
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
          <div>© Anywhere But The West End · London only · Daily index</div>
          <div>Listings sourced from 70 venues</div>
        </footer>
      </body>
    </html>
  );
}
