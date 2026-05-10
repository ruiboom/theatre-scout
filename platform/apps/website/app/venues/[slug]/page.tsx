import { notFound } from 'next/navigation';
import { getVenue } from '@/lib/queries/venues';
import type { VenueDetail } from '@platform/shared';

export const dynamic = 'force-dynamic';

export default async function VenuePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const v = (await getVenue({ slug, include_shows: true })) as VenueDetail | null;
  if (!v) notFound();

  return (
    <article>
      <p style={{ color: 'var(--muted)' }}>
        {v.neighbourhood}
        {v.nearest_tube ? ` · ${v.nearest_tube}` : null}
      </p>
      <h1 style={{ fontSize: '2.4rem', margin: '.25rem 0 1rem' }}>{v.name}</h1>

      {v.description && <p>{v.description}</p>}
      {v.address && (
        <p style={{ color: 'var(--muted)' }}>
          {v.address}
          {v.website ? (
            <>
              {' · '}
              <a href={v.website} target="_blank" rel="noopener noreferrer">
                Website
              </a>
            </>
          ) : null}
        </p>
      )}

      <h2 style={{ marginTop: '2rem' }}>What&rsquo;s on</h2>
      {v.current_shows.length === 0 ? (
        <p style={{ color: 'var(--muted)' }}>Nothing in our database yet.</p>
      ) : (
        v.current_shows.map((s) => (
          <a key={s.id} href={`/shows/${s.slug}`} className="show-card">
            <h2>{s.title}</h2>
            <div className="meta">
              {s.next_performance
                ? new Date(s.next_performance).toLocaleString('en-GB', {
                    day: 'numeric',
                    month: 'short',
                  })
                : 'Dates TBC'}
              {' · '}£{s.price_min}
              {s.price_max && s.price_max !== s.price_min ? `–£${s.price_max}` : ''}
            </div>
          </a>
        ))
      )}
    </article>
  );
}
