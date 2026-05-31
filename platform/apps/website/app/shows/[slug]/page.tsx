import { notFound } from 'next/navigation';
import { getShow, sitemapShows } from '@/lib/queries/shows';
import { fmtDateRange, fmtPrice } from '@/lib/format';
import { trackedExternalHref } from '@/lib/track';

// ISR — show pages change only on the daily scrape. Cached per slug and
// regenerated hourly so crawler sweeps of the detail URLs hit the CDN, not Neon
// (was force-dynamic). Visits tracked client-side via <VisitBeacon>.
export const revalidate = 3600;
// Explicit (this is the default): slugs not returned by generateStaticParams —
// e.g. shows added by the daily scrape after the last deploy — render on demand
// and are then cached, rather than 404ing. Without this guarantee a new show
// would be unreachable until the next deploy.
export const dynamicParams = true;

// Pre-render the current shows at deploy and ISR-cache them; slugs that appear
// between deploys (new shows from the daily scrape) render on first hit and are
// then cached too (dynamicParams defaults true). `generateStaticParams` is what
// puts a dynamic segment on the static/ISR path at all — without it Next treats
// `[slug]` as fully dynamic and re-queries Neon per request. Tolerate a missing
// DB at build by falling back to pure on-demand generation.
export async function generateStaticParams(): Promise<Array<{ slug: string }>> {
  try {
    return (await sitemapShows()).map((s) => ({ slug: s.slug }));
  } catch {
    return [];
  }
}

export default async function ShowPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const show = await getShow({ slug });
  if (!show) notFound();

  return (
    <>
      <div className="crumb">
        <a href="/shows">← All shows</a>
        <span className="crumb-meta">
          / {show.venue.category} / {show.venue.neighbourhood}
        </span>
      </div>

      <section className="show-hero">
        <div className="show-l">
          <div className="ts-meta">
            {show.show_type} · {show.venue.name}
          </div>
          <h1 className="show-title">{show.title}</h1>
          <div className="show-venue">
            <a href={`/venues/${show.venue.slug}`}>{show.venue.name}</a>
            {' · '}
            {show.venue.neighbourhood}
          </div>
          <div className="show-cta">
            {show.booking_url && (
              <a
                className="ts-btn ts-btn--primary"
                href={trackedExternalHref(show.slug, show.booking_url)}
                target="_blank"
                rel="noopener noreferrer"
              >
                Book at {show.venue.name} ↗
              </a>
            )}
          </div>

          <dl className="spec">
            <SpecRow k="Dates" v={fmtDateRange(show.start_date, show.end_date)} />
            <SpecRow k="Price" v={fmtPrice(show.price_min, show.price_max)} />
            {show.duration_minutes && (
              <SpecRow k="Length" v={`${show.duration_minutes} min`} />
            )}
            {show.age_rating && <SpecRow k="Age" v={show.age_rating} />}
            {show.creators.writer && (
              <SpecRow k="Writer" v={show.creators.writer} />
            )}
            {show.creators.director && (
              <SpecRow k="Director" v={show.creators.director} />
            )}
            {show.creators.cast.length > 0 && (
              <SpecRow k="Cast" v={show.creators.cast.join(', ')} />
            )}
            {show.content_warnings.length > 0 && (
              <SpecRow k="Warnings" v={show.content_warnings.join(', ')} />
            )}
          </dl>
        </div>
        <div className="show-r">
          {show.image_url ? (
            <img
              className="show-still"
              src={show.image_url}
              alt={show.title}
              style={{ width: '100%', display: 'block' }}
            />
          ) : (
            <div className="show-still" />
          )}
        </div>
      </section>

      {show.description_full && (
        <section style={{ paddingTop: 24, maxWidth: '60ch' }}>
          <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
            {show.description_full}
          </p>
        </section>
      )}

      {show.performances.length > 0 && (
        <section className="list" style={{ paddingTop: 24 }}>
          <div className="list-head">
            <div className="list-head-mono">
              Performances · {show.performances.length}
            </div>
          </div>
          <div className="row-list">
            {show.performances.slice(0, 60).map((p) => (
              <div key={p.datetime} className="row">
                <div className="row-idx">·</div>
                <div className="row-body">
                  <div className="row-title">
                    {new Date(p.datetime).toLocaleString('en-GB', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                  <div className="row-tag">{p.sold_out ? 'sold out' : 'available'}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function SpecRow({ k, v }: { k: string; v: string | null | undefined }) {
  if (!v) return null;
  return (
    <div className="spec-row">
      <dt className="spec-k">{k}</dt>
      <dd className="spec-v">{v}</dd>
    </div>
  );
}
