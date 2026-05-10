import { notFound } from 'next/navigation';
import { getShow } from '@/lib/queries/shows';

export const dynamic = 'force-dynamic';

export default async function ShowPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const show = await getShow({ slug });
  if (!show) notFound();

  const price =
    show.price_min === show.price_max
      ? `£${show.price_min}`
      : `£${show.price_min}–£${show.price_max}`;

  return (
    <article>
      <p style={{ color: 'var(--muted)' }}>
        <a href={`/venues/${show.venue.slug}`}>{show.venue.name}</a> ·{' '}
        {show.venue.neighbourhood}
      </p>
      <h1 style={{ fontSize: '2.4rem', margin: '0.25rem 0 1rem' }}>
        {show.title}
      </h1>

      <p>
        <strong>{price}</strong>
        {show.duration_minutes ? ` · ${show.duration_minutes} min` : null}
        {show.age_rating ? ` · ${show.age_rating}` : null}
      </p>

      {show.description_full && (
        <div style={{ whiteSpace: 'pre-wrap', marginTop: '1rem' }}>
          {show.description_full}
        </div>
      )}

      {show.performances.length > 0 && (
        <section style={{ marginTop: '2rem' }}>
          <h2>Upcoming performances</h2>
          <ul>
            {show.performances.slice(0, 20).map((p) => (
              <li key={p.datetime}>
                {new Date(p.datetime).toLocaleString('en-GB', {
                  weekday: 'short',
                  day: 'numeric',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
                {p.sold_out ? ' — sold out' : null}
              </li>
            ))}
          </ul>
        </section>
      )}

      {show.booking_url && (
        <p style={{ marginTop: '2rem' }}>
          <a href={show.booking_url} target="_blank" rel="noopener noreferrer">
            Book at {show.venue.name} →
          </a>
        </p>
      )}
    </article>
  );
}
