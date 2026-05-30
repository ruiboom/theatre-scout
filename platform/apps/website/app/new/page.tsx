import type { Show } from '@platform/shared';
import { recentlyAdded } from '@/lib/queries/shows';
import { EditorialFeed } from '@/components/editorial-feed';
import { fmtRelative } from '@/lib/format';
import { trackEvent } from '@/lib/track';

export const dynamic = 'force-dynamic';
export const metadata = {
  title: 'Just announced · Theatre Scout',
  description:
    "The newest shows to appear across London's non-West-End theatres, newest first.",
};

export default async function NewPage() {
  void trackEvent({ type: 'visit', path: '/new' });

  let items: Array<{ show: Show; badge: string | null }> = [];
  let error: string | null = null;
  try {
    const shows = await recentlyAdded(14, 40);
    items = shows.map((s) => ({
      show: s,
      badge: `Added ${fmtRelative(s.first_seen_at)}`,
    }));
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  return (
    <>
      <section className="hero" style={{ padding: '48px 0 24px' }}>
        <div className="hero-l">
          <div className="ts-meta">Just announced · last 14 days</div>
          <h1 className="hero-h1" style={{ fontSize: 'clamp(40px, 5vw, 64px)' }}>
            Just announced.
          </h1>
          <p className="hero-p">
            The newest shows to land across London&rsquo;s non-West-End stages —
            freshly scraped, newest first.
          </p>
          <div className="hero-cta">
            <a className="ts-btn" href="/shows?when=new">
              See more in the index ›
            </a>
          </div>
        </div>
      </section>

      {error ? (
        <p className="empty">Couldn&rsquo;t reach the database — {error}.</p>
      ) : (
        <EditorialFeed items={items} />
      )}
    </>
  );
}
