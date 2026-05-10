import { notFound } from 'next/navigation';
import { getShow } from '@/lib/queries/shows';
import { fmtDateRange, fmtPrice } from '@/lib/format';
import { trackEvent, trackedExternalHref } from '@/lib/track';

export const dynamic = 'force-dynamic';

export default async function ShowPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const show = await getShow({ slug });
  if (!show) notFound();
  void trackEvent({ type: 'visit', path: `/shows/${slug}`, target: slug });

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
