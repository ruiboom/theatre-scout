import { searchShows } from '@/lib/queries/shows';
import type { Show } from '@platform/shared';
import { fmtDateRange, fmtPrice } from '@/lib/format';
import { londonToday, resolveWindow } from '@/lib/time';
import { pickOne } from '@/lib/random';
import { trackEvent, trackedExternalHref } from '@/lib/track';

export const dynamic = 'force-dynamic';
export const metadata = {
  title: 'Take a punt · Theatre Scout',
  description:
    'One show, picked at random from everything on tonight outside the West End. Not for you? Spin again.',
};

type Search = Record<string, string | string[] | undefined>;

function pickStr(v: string | string[] | undefined): string {
  if (Array.isArray(v)) return v[0] ?? '';
  return v ?? '';
}

const WINDOWS = [
  { key: 'tonight', label: 'Tonight' },
  { key: 'weekend', label: 'This weekend' },
] as const;

const BUDGETS = [
  { key: '15', label: 'Under £15' },
  { key: '25', label: 'Under £25' },
  { key: '', label: 'Any price' },
] as const;

/**
 * Compose a /punt URL, omitting defaults so the canonical "tonight, any price,
 * first roll" punt is just `/punt`.
 */
function puntUrl(opts: { when: string; max_price: string; s: number }): string {
  const p = new URLSearchParams();
  if (opts.when && opts.when !== 'tonight') p.set('when', opts.when);
  if (opts.max_price) p.set('max_price', opts.max_price);
  if (opts.s !== 1) p.set('s', String(opts.s));
  const qs = p.toString();
  return qs ? `/punt?${qs}` : '/punt';
}

export default async function PuntPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const sp = await searchParams;
  void trackEvent({ type: 'visit', path: '/punt' });

  const when = pickStr(sp.when) === 'weekend' ? 'weekend' : 'tonight';
  const budgetKey = ['15', '25'].includes(pickStr(sp.max_price))
    ? pickStr(sp.max_price)
    : '';
  const maxPrice = budgetKey === '15' ? 15 : budgetKey === '25' ? 25 : undefined;
  const seedRaw = Number.parseInt(pickStr(sp.s), 10);
  const seed = Number.isFinite(seedRaw) && seedRaw > 0 ? seedRaw : 1;

  const todayIso = londonToday();
  const { from, to } =
    when === 'weekend'
      ? resolveWindow('this_weekend')
      : { from: todayIso, to: todayIso };

  let pool: Show[] = [];
  let error: string | null = null;
  try {
    const result = await searchShows({
      date_from: from,
      date_to: to,
      max_price: maxPrice,
      min_price: 0,
      limit: 200,
    });
    pool = result.shows;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  // Pool hygiene: searchShows deliberately INCLUDES shows with no start_date
  // (better a "When?" gap on the index than a false negative). For a punt that's
  // wrong — only keep shows whose run genuinely covers the chosen window. ISO
  // date strings compare lexicographically, so string comparison is safe here.
  const candidates = pool.filter((s) => {
    if (!s.start_date) return false;
    if (s.start_date > to) return false; // starts after the window
    if (s.end_date && s.end_date < from) return false; // already closed
    return true;
  });

  const show = pickOne(candidates, seed);

  const windowLabel = when === 'weekend' ? 'This weekend' : 'Tonight';
  const budgetLabel = maxPrice ? `under £${maxPrice}` : 'any price';
  const indexHref = when === 'weekend' ? '/shows?when=week' : '/shows?when=today';

  return (
    <>
      <section className="hero" style={{ padding: '48px 0 24px' }}>
        <div className="hero-l">
          <div className="ts-meta">
            Take a punt · {windowLabel} · {budgetLabel}
          </div>
          <h1 className="hero-h1" style={{ fontSize: 'clamp(40px, 5vw, 64px)' }}>
            {when === 'weekend' ? 'A weekend punt.' : "Tonight's punt."}
          </h1>
          <p className="hero-p">
            One show, picked at random from everything{' '}
            {when === 'weekend' ? 'on this weekend' : 'on tonight'}
            {maxPrice ? ` under £${maxPrice}` : ''}. Not for you? Spin again.
          </p>
        </div>
      </section>

      <section className="controls" style={{ marginBottom: 24 }}>
        <div className="controls-l tabs">
          {WINDOWS.map((w) => (
            <a
              key={w.key}
              className={`ts-chip ${when === w.key ? 'ts-chip--active' : ''}`}
              href={puntUrl({ when: w.key, max_price: budgetKey, s: 1 })}
            >
              {w.label}
            </a>
          ))}
        </div>
        <div className="controls-r tabs">
          {BUDGETS.map((b) => (
            <a
              key={b.key || 'any'}
              className={`ts-chip ${budgetKey === b.key ? 'ts-chip--active' : ''}`}
              href={puntUrl({ when, max_price: b.key, s: 1 })}
            >
              {b.label}
            </a>
          ))}
        </div>
      </section>

      {error ? (
        <p className="empty">Couldn&rsquo;t reach the database — {error}.</p>
      ) : show ? (
        <>
          <section className="show-hero">
            <div className="show-l">
              <div className="ts-meta">
                {show.show_type} · {show.venue.name}
              </div>
              <h2 className="show-title">{show.title}</h2>
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
                <a
                  className="ts-btn"
                  href={puntUrl({ when, max_price: budgetKey, s: seed + 1 })}
                >
                  Spin again ↻
                </a>
              </div>
              <dl className="spec">
                <SpecRow k="Dates" v={fmtDateRange(show.start_date, show.end_date)} />
                <SpecRow k="Price" v={fmtPrice(show.price_min, show.price_max)} />
                {show.duration_minutes && (
                  <SpecRow k="Length" v={`${show.duration_minutes} min`} />
                )}
                {show.age_rating && <SpecRow k="Age" v={show.age_rating} />}
                {show.content_warnings.length > 0 && (
                  <SpecRow k="Warnings" v={show.content_warnings.join(', ')} />
                )}
              </dl>
              {show.description_short && (
                <p style={{ maxWidth: '54ch', lineHeight: 1.5 }}>
                  {show.description_short}
                </p>
              )}
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

          <section style={{ paddingTop: 24 }}>
            <a className="ts-btn" href={indexHref}>
              See everything {when === 'weekend' ? 'this weekend' : 'on tonight'} →
            </a>
          </section>
        </>
      ) : (
        <section className="show-hero">
          <div className="show-l">
            <h2 className="show-title">
              No punt {when === 'weekend' ? 'this weekend' : 'tonight'}
              {maxPrice ? ` under £${maxPrice}` : ''}.
            </h2>
            <p className="hero-p">Nothing matched — widen the net:</p>
            <div className="show-cta">
              {maxPrice && (
                <a className="ts-btn" href={puntUrl({ when, max_price: '', s: 1 })}>
                  Any price
                </a>
              )}
              {when !== 'weekend' && (
                <a
                  className="ts-btn"
                  href={puntUrl({ when: 'weekend', max_price: budgetKey, s: 1 })}
                >
                  Try this weekend
                </a>
              )}
              <a className="ts-btn ts-btn--primary" href="/shows">
                Browse the index ›
              </a>
            </div>
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
