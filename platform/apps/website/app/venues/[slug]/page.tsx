import { notFound } from 'next/navigation';
import { getVenue, sitemapVenues } from '@/lib/queries/venues';
import type { VenueDetail } from '@platform/shared';
import { fmtDateRange, fmtPrice, pad3 } from '@/lib/format';
import { VenueMap } from '@/components/venue-map';
import { trackedExternalHref } from '@/lib/track';

// ISR — venue pages change only on the daily scrape. Cached per slug and
// regenerated hourly so the hundreds of detail URLs crawlers sweep are served
// from the CDN, not Neon (was force-dynamic). Visits tracked client-side via
// <VisitBeacon> in the layout — `topVenueClicks` keys off the `/venues/<slug>`
// path it records, so the admin metric is unaffected.
export const revalidate = 3600;
// See shows/[slug]: unknown slugs render on demand + cache rather than 404.
export const dynamicParams = true;

// Pre-render all venues at deploy onto the ISR path (see the matching note in
// shows/[slug]). Without `generateStaticParams`, Next would keep `[slug]` fully
// dynamic and hit Neon per request. Tolerant of a missing DB at build.
export async function generateStaticParams(): Promise<Array<{ slug: string }>> {
  try {
    return (await sitemapVenues()).map((v) => ({ slug: v.slug }));
  } catch {
    return [];
  }
}

export default async function VenuePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const v = (await getVenue({ slug, include_shows: true })) as VenueDetail | null;
  if (!v) notFound();

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
