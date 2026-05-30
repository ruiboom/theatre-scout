import type { Show } from '@platform/shared';
import { closingSoon } from '@/lib/queries/shows';
import { EditorialFeed } from '@/components/editorial-feed';
import { londonToday } from '@/lib/time';
import { trackEvent } from '@/lib/track';

export const dynamic = 'force-dynamic';
export const metadata = {
  title: 'Closing soon · Theatre Scout',
  description:
    'London non-West-End shows finishing their run within a fortnight — last chance to catch them.',
};

function daysUntil(endIso: string | null, todayIso: string): number | null {
  if (!endIso) return null;
  return Math.round(
    (Date.parse(`${endIso}T00:00:00Z`) - Date.parse(`${todayIso}T00:00:00Z`)) /
      86_400_000,
  );
}

function closingBadge(d: number | null): string | null {
  if (d == null) return null;
  if (d <= 0) return 'Last day';
  if (d === 1) return 'Closes tomorrow';
  return `Closes in ${d} days`;
}

export default async function ClosingPage() {
  void trackEvent({ type: 'visit', path: '/closing' });
  const todayIso = londonToday();

  let items: Array<{ show: Show; badge: string | null }> = [];
  let error: string | null = null;
  try {
    const shows = await closingSoon(14, 40);
    items = shows.map((s) => ({
      show: s,
      badge: closingBadge(daysUntil(s.end_date, todayIso)),
    }));
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  return (
    <>
      <section className="hero" style={{ padding: '48px 0 24px' }}>
        <div className="hero-l">
          <div className="ts-meta">Closing soon · next 14 days</div>
          <h1 className="hero-h1" style={{ fontSize: 'clamp(40px, 5vw, 64px)' }}>
            Last chance.
          </h1>
          <p className="hero-p">
            Shows finishing their run within a fortnight — catch them before
            they close.
          </p>
          <div className="hero-cta">
            <a className="ts-btn" href="/shows">
              Browse the full index ›
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
