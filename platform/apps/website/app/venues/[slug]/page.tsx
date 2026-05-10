import { notFound } from 'next/navigation';
import { getVenue } from '@/lib/queries/venues';
import type { VenueDetail } from '@platform/shared';
import { fmtDateRange, fmtPrice, pad3 } from '@/lib/format';
import { VenueMap } from '@/components/venue-map';
import { trackEvent, trackedExternalHref } from '@/lib/track';

export const dynamic = 'force-dynamic';

export default async function VenuePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const v = (await getVenue({ slug, include_shows: true })) as VenueDetail | null;
  if (!v) notFound();
  void trackEvent({ type: 'visit', path: `/venues/${slug}`, target: slug });

  const shows = v.current_shows;

  return (
    <>
      <div className="crumb">
        <a href="/">← All theatres</a>
        <span className="crumb-meta">
          / {v.category} / {v.neighbourhood}
        </span>
      </div>

      <section className="show-hero">
        <div className="show-l">
          <div className="ts-meta">
            {String(shows.length).padStart(4, '0')} · {v.category} venue
          </div>
          <h1 className="show-title">{v.name}</h1>
          <div className="show-venue">
            {v.neighbourhood}
            {v.postcode_prefix ? ` · ${v.postcode_prefix}` : ''}
          </div>
          <div className="show-cta">
            {v.website && (
              <a
                className="ts-btn ts-btn--primary"
                href={v.website}
                target="_blank"
                rel="noopener noreferrer"
              >
                Box office ↗
              </a>
            )}
            <a className="ts-btn" href={`/shows?cat=${v.category}`}>
              Other {v.category} venues
            </a>
          </div>
        </div>
        <div className="show-r">
          {v.lat != null && v.lng != null ? (
            <VenueMap lat={v.lat} lng={v.lng} name={v.name} />
          ) : (
            <div className="show-still" />
          )}
        </div>
      </section>

      {shows.length === 0 ? (
        <p className="empty">No shows scraped yet for this venue.</p>
      ) : (
        <section className="list" style={{ paddingTop: 24 }}>
          <div className="list-head">
            <div className="list-head-mono">
              Programme · {shows.length} shows
            </div>
          </div>
          <div className="row-list">
            {shows.map((s, i) => (
              <div key={s.id} className="row">
                <div className="row-idx">{pad3(i + 1)}</div>
                <div className="thumb">
                  {s.image_url && (
                    <img src={s.image_url} alt="" loading="lazy" />
                  )}
                </div>
                <div className="row-body">
                  <a
                    className="row-title"
                    href={trackedExternalHref(s.slug, s.booking_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={s.description_short || undefined}
                  >
                    {s.title}{' '}
                    <span className="row-title-arrow" aria-hidden>
                      ↗
                    </span>
                  </a>
                  <div className="row-tag">
                    {s.show_type}
                    {s.price_min != null
                      ? ` · ${fmtPrice(s.price_min, s.price_max)}`
                      : ''}
                  </div>
                </div>
                <div className="row-venue">
                  {s.description_short
                    ? s.description_short.length > 80
                      ? s.description_short.slice(0, 80).trimEnd() + '…'
                      : s.description_short
                    : ''}
                </div>
                <div className="row-dates">
                  {fmtDateRange(s.start_date, s.end_date)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
