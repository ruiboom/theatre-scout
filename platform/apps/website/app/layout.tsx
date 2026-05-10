import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Anywhere But The West End',
    template: '%s — Anywhere But The West End',
  },
  description:
    "London's other theatre scene. Pub theatres, fringe spaces, converted warehouses — where the interesting work happens.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <a href="/" className="brand">
            Anywhere But The West End
          </a>
          <nav>
            <a href="/shows">Shows</a>
            <a href="/venues">Venues</a>
            <a href="/about">About</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="site-footer">
          <p>
            Independent. Not affiliated with any venue. Listings sourced from{' '}
            <a href="/about">70 theatres across London</a>.
          </p>
        </footer>
      </body>
    </html>
  );
}
