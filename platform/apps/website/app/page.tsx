import { searchShows } from '@/lib/queries/shows';
import type { Show } from '@platform/shared';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let shows: Show[] = [];
  let error: string | null = null;
  try {
    const result = await searchShows({ limit: 20, min_price: 0 });
    shows = result.shows;
  } catch (err) {
    error = err instanceof Error ? err.message : 'Database not available';
  }

  return (
    <>
      <section style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', margin: 0 }}>
          Anywhere But The West End
        </h1>
        <p style={{ fontSize: '1.15rem', color: 'var(--muted)' }}>
          There are two theatre scenes in London. One has billboards. The other
          is where the interesting work happens.
        </p>
      </section>

      <h2 style={{ borderBottom: '1px solid var(--rule)', paddingBottom: '.5rem' }}>
        On this week
      </h2>

      {error ? (
        <div className="empty-state">
          <p>Couldn&rsquo;t reach the database.</p>
          <p style={{ fontSize: '.85rem' }}>{error}</p>
        </div>
      ) : shows.length === 0 ? (
        <div className="empty-state">
          <p>No shows yet — run a scrape to populate the database.</p>
          <code>uv run scrape all</code>
        </div>
      ) : (
        shows.map((s) => <ShowCard key={s.id} show={s} />)
      )}
    </>
  );
}

function ShowCard({ show }: { show: Show }) {
  const date = show.next_performance
    ? new Date(show.next_performance).toLocaleString('en-GB', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
      })
    : 'Dates TBC';
  const price =
    show.price_min === show.price_max
      ? `£${show.price_min}`
      : `£${show.price_min}–£${show.price_max}`;
  return (
    <a className="show-card" href={`/shows/${show.slug}`}>
      <h2>{show.title}</h2>
      <div className="meta">
        {show.venue.name} · {show.venue.neighbourhood} · {date} · {price}
      </div>
      {show.description_short && (
        <p style={{ marginTop: '.4rem' }}>{show.description_short}</p>
      )}
    </a>
  );
}
