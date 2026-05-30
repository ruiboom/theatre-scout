import type { Show } from '@platform/shared';
import { fmtDateRange, fmtPrice } from '@/lib/format';
import { trackedExternalHref } from '@/lib/track';

/**
 * Magazine-style feed shared by /new and /closing: big art, kicker, a large
 * tracked title, dates + price, and the short description visible. Each item's
 * `badge` is computed by the page ("Added 2d ago" / "Closes in 5 days").
 */
export function EditorialFeed({
  items,
}: {
  items: Array<{ show: Show; badge: string | null }>;
}) {
  if (items.length === 0) {
    return (
      <p className="empty">
        Nothing here right now — check back after the next refresh.
      </p>
    );
  }
  return (
    <div className="feature-list">
      {items.map(({ show, badge }) => {
        const price = fmtPrice(show.price_min, show.price_max);
        return (
          <article className="feature" key={show.id}>
            <div className="feature-art">
              {show.image_url ? (
                <img src={show.image_url} alt="" loading="lazy" />
              ) : (
                <div className="feature-art-empty" aria-hidden />
              )}
            </div>
            <div className="feature-body">
              <div className="feature-kicker">
                {badge && <span className="feature-badge">{badge}</span>}
                <span>
                  {show.show_type} · {show.venue.neighbourhood}
                </span>
              </div>
              <h2 className="feature-title">
                <a
                  href={trackedExternalHref(show.slug, show.booking_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {show.title}
                  <span aria-hidden> ↗</span>
                </a>
              </h2>
              <a className="feature-venue" href={`/venues/${show.venue.slug}`}>
                {show.venue.name}
              </a>
              <div className="feature-meta">
                {fmtDateRange(show.start_date, show.end_date)}
                {price ? ` · ${price}` : ''}
              </div>
              {show.description_short && (
                <p className="feature-desc">{show.description_short}</p>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
