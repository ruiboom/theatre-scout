import { searchShows } from '@/lib/queries/shows';
import type { Show, ShowType, VenueCategory } from '@platform/shared';
import { fmtDateRange, fmtPrice, pad2, pad3 } from '@/lib/format';
import { trackEvent, trackedExternalHref } from '@/lib/track';

export const dynamic = 'force-dynamic';

const CATEGORIES: Array<{ key: VenueCategory; label: string }> = [
  { key: 'major', label: 'Major producing houses' },
  { key: 'mid', label: 'Mid-sized & specialist' },
  { key: 'fringe', label: 'Fringe & pub' },
  { key: 'outer', label: 'Outer London' },
];
const SHOW_TYPES = [
  'play',
  'musical',
  'comedy',
  'dance',
  'opera',
  'family',
  'cabaret',
  'other',
] as const;
const SHOW_TYPE_RAILS: Array<{ key: ShowType; label: string }> = [
  { key: 'play', label: 'Plays' },
  { key: 'musical', label: 'Musicals' },
  { key: 'comedy', label: 'Comedy' },
  { key: 'dance', label: 'Dance' },
  { key: 'opera', label: 'Opera' },
  { key: 'family', label: 'Family' },
  { key: 'cabaret', label: 'Cabaret' },
  { key: 'other', label: 'Other' },
];
const RAIL_PICK_LIMIT = 4;

/**
 * Pick up to `n` random items from `arr`. Used on the rails view so each
 * page load surfaces a different slice of what's playing — the rail's
 * "View all" link is there for the deterministic full list.
 */
function sampleRandom<T>(arr: T[], n: number): T[] {
  const copy = [...arr];
  const take = Math.min(n, copy.length);
  for (let i = 0; i < take; i++) {
    const j = i + Math.floor(Math.random() * (copy.length - i));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy.slice(0, take);
}

type Search = Record<string, string | string[] | undefined>;

function pickStr(v: string | string[] | undefined): string {
  if (Array.isArray(v)) return v[0] ?? '';
  return v ?? '';
}

/**
 * Compose a /shows URL with the current filter state, replacing whichever
 * params the caller passes in. Mirrors scout's `chip_url` jinja helper.
 */
function buildChipUrl(current: Record<string, string>, changes: Record<string, string>): string {
  const merged = { ...current, ...changes };
  if (merged.view === 'rails') merged.view = '';
  const cleaned = Object.entries(merged).filter(([, v]) => v && v.length > 0);
  if (cleaned.length === 0) return '/shows';
  return '/shows?' + new URLSearchParams(cleaned).toString();
}

export default async function ShowsPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const sp = await searchParams;
  const q = pickStr(sp.q);

  // Page view + (if there's a search query) search tracking, fire-and-forget.
  void trackEvent({ type: 'visit', path: '/shows' });
  if (q) void trackEvent({ type: 'search', query: q });
  const filterType = pickStr(sp.type);
  const filterCat = pickStr(sp.cat) as '' | VenueCategory;
  const filterWhen = pickStr(sp.when); // '', 'today', 'week', 'new'
  const sortField = pickStr(sp.sort) || 'start_date';
  const sortDir = pickStr(sp.dir) || 'asc';
  const view = (pickStr(sp.view) || 'rails') as 'rails' | 'list';

  const today = new Date();
  const fmtIso = (d: Date) => d.toISOString().slice(0, 10);
  let date_from: string | undefined;
  let date_to: string | undefined;
  if (filterWhen === 'today') {
    date_from = fmtIso(today);
    date_to = fmtIso(today);
  } else if (filterWhen === 'week') {
    date_from = fmtIso(today);
    date_to = fmtIso(new Date(today.getTime() + 7 * 86400_000));
  } else if (filterWhen === 'new') {
    // "New" means first_seen_at within the last 14 days. The query layer
    // doesn't expose that directly yet — same default window for now, the
    // ordering brings the most-recently-added rows up.
    date_from = fmtIso(today);
    date_to = fmtIso(new Date(today.getTime() + 365 * 86400_000));
  } else {
    date_from = fmtIso(today);
    date_to = fmtIso(new Date(today.getTime() + 365 * 86400_000));
  }

  let shows: Show[] = [];
  let error: string | null = null;
  try {
    const result = await searchShows({
      q: q || undefined,
      show_type:
        (SHOW_TYPES as readonly string[]).includes(filterType)
          ? (filterType as Show['show_type'])
          : undefined,
      category: filterCat || undefined,
      sort: (['start_date', 'end_date', 'title', 'venue'] as const).includes(
        sortField as 'start_date',
      )
        ? (sortField as 'start_date')
        : 'start_date',
      dir: sortDir === 'desc' ? 'desc' : 'asc',
      date_from,
      date_to,
      limit: 200,
      min_price: 0,
    });
    shows = result.shows;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  const current = {
    q,
    type: filterType,
    cat: filterCat,
    when: filterWhen,
    view,
    sort: sortField === 'start_date' ? '' : sortField,
    dir: sortDir === 'asc' ? '' : sortDir,
  };
  const chipUrl = (changes: Record<string, string>) => buildChipUrl(current, changes);

  // Hidden inputs for the search form preserve every filter except q.
  const carry = Object.entries(current).filter(([k, v]) => v && k !== 'q');

  // Bucket into rails for the rails view: by show type first, then by venue tier.
  const typeRails = SHOW_TYPE_RAILS.map(({ key, label }) => {
    const inType = shows.filter((s) => s.show_type === key);
    return {
      kind: 'type' as const,
      key,
      label,
      total: inType.length,
      picks: sampleRandom(inType, RAIL_PICK_LIMIT),
    };
  });
  const categoryRails = CATEGORIES.map(({ key, label }) => {
    const inCat = shows.filter((s) => s.venue.category === key);
    return {
      kind: 'category' as const,
      key,
      label,
      total: inCat.length,
      picks: sampleRandom(inCat, RAIL_PICK_LIMIT),
    };
  });
  const rails = [...typeRails, ...categoryRails];

  return (
    <>
      <section className="hero" style={{ padding: '48px 0 32px' }}>
        <div className="hero-l">
          <div className="ts-meta">
            Index · {shows.length.toLocaleString()} listings
          </div>
          <h1 className="hero-h1" style={{ fontSize: 'clamp(48px, 5vw, 72px)' }}>
            Shows playing
            <br />
            in London.
          </h1>
        </div>
      </section>

      <section className="controls">
        <div className="controls-l tabs">
          <Chip active={!filterWhen} href={chipUrl({ when: '' })}>
            All
          </Chip>
          <Chip active={filterWhen === 'today'} href={chipUrl({ when: 'today' })}>
            Today
          </Chip>
          <Chip active={filterWhen === 'week'} href={chipUrl({ when: 'week' })}>
            This week
          </Chip>
          <Chip active={filterWhen === 'new'} href={chipUrl({ when: 'new' })}>
            New
          </Chip>
        </div>
        <div className="controls-r">
          <form className="search" method="get" action="/shows">
            {carry.map(([k, v]) => (
              <input key={k} type="hidden" name={k} value={v} />
            ))}
            <input
              type="search"
              name="q"
              defaultValue={q}
              placeholder="Search title…"
              aria-label="Search title"
            />
          </form>
          <div className="tabs">
            <Chip active={view === 'rails'} href={chipUrl({ view: 'rails' })}>
              Rails
            </Chip>
            <Chip active={view === 'list'} href={chipUrl({ view: 'list' })}>
              List
            </Chip>
          </div>
        </div>
      </section>

      <details className="filters" open={Boolean(filterType || filterCat)}>
        <summary>
          Filters · {(filterType ? 1 : 0) + (filterCat ? 1 : 0)} active
        </summary>
        <div className="filter-body">
          <div className="filter-group">
            <div className="filter-group-label">Type</div>
            <div className="filter-row">
              <Chip active={!filterType} href={chipUrl({ type: '' })}>
                All
              </Chip>
              {SHOW_TYPES.map((t) => (
                <Chip
                  key={t}
                  active={filterType === t}
                  href={chipUrl({ type: t })}
                >
                  {t}
                </Chip>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <div className="filter-group-label">Venue tier</div>
            <div className="filter-row">
              <Chip active={!filterCat} href={chipUrl({ cat: '' })}>
                All
              </Chip>
              {CATEGORIES.map(({ key, label }) => (
                <Chip
                  key={key}
                  active={filterCat === key}
                  href={chipUrl({ cat: key })}
                >
                  {label.split(' ')[0]}
                </Chip>
              ))}
            </div>
          </div>
        </div>
      </details>

      {view === 'list' && (
        <div className="sort-bar">
          <span className="sort-bar-label">Sort by</span>
          {(
            [
              ['start_date', 'Opening'],
              ['end_date', 'Closing'],
              ['title', 'Title'],
              ['venue', 'Venue'],
            ] as const
          ).map(([field, label]) => {
            const active = sortField === field;
            const nextDir = active && sortDir === 'asc' ? 'desc' : 'asc';
            return (
              <a
                key={field}
                className={`sort-link ${active ? 'active' : ''}`}
                href={chipUrl({
                  sort: field === 'start_date' ? '' : field,
                  dir: nextDir === 'asc' ? '' : nextDir,
                })}
              >
                {label}
                {active && (
                  <span className="sort-arrow">
                    {sortDir === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </a>
            );
          })}
        </div>
      )}

      {error ? (
        <p className="empty">Couldn&rsquo;t reach the database — {error}.</p>
      ) : shows.length === 0 ? (
        <p className="empty">No shows match. Try clearing filters.</p>
      ) : view === 'rails' ? (
        rails.map(
          (rail, i) =>
            rail.total > 0 && (
              <section key={`${rail.kind}-${rail.key}`} className="rail">
                <div className="rail-head">
                  <div className="rail-idx">{pad2(i + 1)}</div>
                  <h2 className="rail-title">
                    {rail.label} <small>{rail.total} shows</small>
                  </h2>
                  <a
                    className="rail-count"
                    href={chipUrl(
                      rail.kind === 'type'
                        ? { type: rail.key, view: 'list' }
                        : { cat: rail.key, view: 'list' },
                    )}
                  >
                    View all ›
                  </a>
                </div>
                <div className="rail-grid">
                  {rail.picks.map((s) => (
                    <ShowCard key={s.id} show={s} />
                  ))}
                </div>
              </section>
            ),
        )
      ) : (
        <section className="list">
          <div className="list-head">
            <div className="list-head-mono">
              All shows · {shows.length.toLocaleString()}
            </div>
          </div>
          <div className="row-list">
            {shows.map((s, i) => (
              <ShowRow key={s.id} idx={i + 1} show={s} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

// ---- atoms ---------------------------------------------------------------

function Chip({
  active,
  href,
  children,
}: {
  active: boolean;
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a className={`ts-chip ${active ? 'ts-chip--active' : ''}`} href={href}>
      {children}
    </a>
  );
}

function ShowCard({ show }: { show: Show }) {
  return (
    <div className="card">
      <div className="thumb">
        {show.image_url && (
          <img src={show.image_url} alt="" loading="lazy" />
        )}
      </div>
      <div className="card-meta">{show.show_type}</div>
      <a
        className="card-title"
        href={trackedExternalHref(show.slug, show.booking_url)}
        target="_blank"
        rel="noopener noreferrer"
        title={show.description_short || undefined}
      >
        {show.title}{' '}
        <span className="card-title-arrow" aria-hidden>
          ↗
        </span>
      </a>
      <a className="card-sub" href={`/venues/${show.venue.slug}`}>
        {show.venue.name}
      </a>
      <div className="card-dates">
        {fmtDateRange(show.start_date, show.end_date)}
      </div>
    </div>
  );
}

function ShowRow({ idx, show }: { idx: number; show: Show }) {
  return (
    <div className="row">
      <div className="row-idx">{pad3(idx)}</div>
      <div className="thumb">
        {show.image_url && (
          <img src={show.image_url} alt="" loading="lazy" />
        )}
      </div>
      <div className="row-body">
        <a
          className="row-title"
          href={trackedExternalHref(show.slug, show.booking_url)}
          target="_blank"
          rel="noopener noreferrer"
          title={show.description_short || undefined}
        >
          {show.title}{' '}
          <span className="row-title-arrow" aria-hidden>
            ↗
          </span>
        </a>
        <div className="row-tag">{show.show_type}</div>
      </div>
      <a className="row-venue" href={`/venues/${show.venue.slug}`}>
        {show.venue.name}
      </a>
      <div className="row-dates">{fmtDateRange(show.start_date, show.end_date)}</div>
      <div className="row-aside">{fmtPrice(show.price_min, show.price_max)}</div>
    </div>
  );
}
