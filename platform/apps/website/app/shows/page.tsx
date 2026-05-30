import { openingsByDay, searchShows } from '@/lib/queries/shows';
import type { Show, ShowType, VenueCategory } from '@platform/shared';
import { fmtDateRange, fmtPrice, pad2, pad3 } from '@/lib/format';
import { londonToday } from '@/lib/time';
import {
  addMonths,
  dayLabel,
  monthGrid,
  monthLabel,
  monthParam,
  parseMonth,
  WEEKDAY_HEADERS,
  type DayCell,
} from '@/lib/calendar';
import { trackEvent, trackedExternalHref } from '@/lib/track';
import { sampleRandom } from '@/lib/random';

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
  // `cal` (which month the grid shows) only means anything in calendar view.
  if (merged.view !== 'calendar') merged.cal = '';
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
  const filterWhen = pickStr(sp.when); // '', 'today', 'week', 'new', 'closing'
  const filterDate = /^\d{4}-\d{2}-\d{2}$/.test(pickStr(sp.date))
    ? pickStr(sp.date)
    : '';
  const cal = pickStr(sp.cal); // which month the calendar grid shows, 'YYYY-MM'
  const sortField = pickStr(sp.sort) || 'start_date';
  const sortDir = pickStr(sp.dir) || 'asc';
  const view = (pickStr(sp.view) || 'rails') as 'rails' | 'list' | 'calendar';

  const showType = (SHOW_TYPES as readonly string[]).includes(filterType)
    ? (filterType as Show['show_type'])
    : undefined;

  const todayIso = londonToday();
  const addDaysIso = (iso: string, n: number) =>
    new Date(new Date(iso + 'T00:00:00Z').getTime() + n * 86400_000)
      .toISOString()
      .slice(0, 10);

  // A picked `date` is a single-day filter in every view — "Today" generalised
  // to any day. The `when` presets are ranges and only apply to rails/list.
  // Calendar view always lists one day: the picked date, else today.
  const effectiveDate = filterDate || todayIso;
  let date_from: string;
  let date_to: string;
  if (filterDate || view === 'calendar') {
    date_from = effectiveDate;
    date_to = effectiveDate;
  } else if (filterWhen === 'today') {
    date_from = todayIso;
    date_to = todayIso;
  } else if (filterWhen === 'week') {
    date_from = todayIso;
    date_to = addDaysIso(todayIso, 7);
  } else if (filterWhen === 'new') {
    // "Just announced": first seen within 14 days (applied as a filter below).
    // Keep a wide run window so upcoming-but-not-yet-open shows still appear.
    date_from = todayIso;
    date_to = addDaysIso(todayIso, 365);
  } else if (filterWhen === 'closing') {
    // "Closing soon": runs ending within the next 14 days.
    date_from = todayIso;
    date_to = addDaysIso(todayIso, 14);
  } else {
    date_from = todayIso;
    date_to = addDaysIso(todayIso, 365);
  }

  const firstSeenWithinDays = filterWhen === 'new' ? 14 : undefined;
  const closingWithinDays = filterWhen === 'closing' ? 14 : undefined;

  // The New / Closing-soon chips imply a default ordering (newest-added /
  // soonest-closing) unless the user picked a sort explicitly via the sort bar.
  const explicitSort = (
    ['start_date', 'end_date', 'title', 'venue'] as const
  ).includes(pickStr(sp.sort) as 'start_date');
  const querySort = explicitSort
    ? (pickStr(sp.sort) as 'start_date' | 'end_date' | 'title' | 'venue')
    : filterWhen === 'new'
      ? 'first_seen'
      : filterWhen === 'closing'
        ? 'end_date'
        : 'start_date';
  const queryDir: 'asc' | 'desc' =
    pickStr(sp.dir) === 'desc'
      ? 'desc'
      : pickStr(sp.dir) === 'asc'
        ? 'asc'
        : filterWhen === 'new'
          ? 'desc'
          : 'asc';

  let shows: Show[] = [];
  let error: string | null = null;
  try {
    const result = await searchShows({
      q: q || undefined,
      show_type: showType,
      category: filterCat || undefined,
      sort: querySort,
      dir: queryDir,
      date_from,
      date_to,
      first_seen_within_days: firstSeenWithinDays,
      closing_within_days: closingWithinDays,
      limit: 200,
      min_price: 0,
    });
    shows = result.shows;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  // Calendar view also needs per-day opening counts for the visible month grid.
  let calYear = 0;
  let calMonth = 0;
  let calWeeks: DayCell[][] = [];
  const openings = new Map<string, number>();
  if (view === 'calendar') {
    const ym = parseMonth(cal, effectiveDate);
    calYear = ym.year;
    calMonth = ym.month;
    calWeeks = monthGrid(calYear, calMonth);
    try {
      const rows = await openingsByDay(calWeeks[0]![0]!.iso, calWeeks[5]![6]!.iso, {
        category: filterCat || undefined,
        show_type: showType,
        q: q || undefined,
      });
      for (const r of rows) openings.set(r.day, r.count);
    } catch {
      // Grid still renders, just without the opening badges.
    }
  }

  const current = {
    q,
    type: filterType,
    cat: filterCat,
    when: filterWhen,
    date: filterDate,
    cal: view === 'calendar' ? cal : '',
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
          {view === 'calendar' ? (
            <span className="ts-chip ts-chip--active">{dayLabel(effectiveDate)}</span>
          ) : (
            <>
              <Chip
                active={!filterWhen && !filterDate}
                href={chipUrl({ when: '', date: '' })}
              >
                All
              </Chip>
              <Chip
                active={filterWhen === 'today' && !filterDate}
                href={chipUrl({ when: 'today', date: '' })}
              >
                Today
              </Chip>
              <Chip
                active={filterWhen === 'week' && !filterDate}
                href={chipUrl({ when: 'week', date: '' })}
              >
                This week
              </Chip>
              <Chip
                active={filterWhen === 'new' && !filterDate}
                href={chipUrl({ when: 'new', date: '' })}
              >
                New
              </Chip>
              <Chip
                active={filterWhen === 'closing' && !filterDate}
                href={chipUrl({ when: 'closing', date: '' })}
              >
                Closing soon
              </Chip>
              {filterDate && (
                <span className="cal-datechip">
                  <a
                    className="ts-chip ts-chip--active"
                    href={chipUrl({ view: 'calendar' })}
                  >
                    {dayLabel(filterDate)}
                  </a>
                  <a
                    className="cal-datechip-x"
                    href={chipUrl({ date: '', cal: '' })}
                    aria-label="Clear date"
                  >
                    ×
                  </a>
                </span>
              )}
            </>
          )}
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
              placeholder="Search…"
              aria-label="Search"
            />
          </form>
          <div className="tabs">
            <Chip active={view === 'rails'} href={chipUrl({ view: 'rails' })}>
              Rails
            </Chip>
            <Chip active={view === 'list'} href={chipUrl({ view: 'list' })}>
              List
            </Chip>
            <Chip
              active={view === 'calendar'}
              href={chipUrl({ view: 'calendar', when: '' })}
            >
              Calendar
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
            const active = querySort === field;
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

      {view === 'calendar' ? (
        <CalendarView
          year={calYear}
          month={calMonth}
          weeks={calWeeks}
          todayIso={todayIso}
          selectedIso={effectiveDate}
          openings={openings}
          shows={shows}
          error={error}
          chipUrl={chipUrl}
        />
      ) : error ? (
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

/**
 * Month grid + selected-day list. Pure presentation — the grid is a set of
 * links (month nav, day select are URL changes), so the whole calendar stays
 * server-rendered with no client JS, matching the rest of the page. Cells with
 * openings carry a count badge; today and the selected day get their own marks.
 */
function CalendarView({
  year,
  month,
  weeks,
  todayIso,
  selectedIso,
  openings,
  shows,
  error,
  chipUrl,
}: {
  year: number;
  month: number;
  weeks: DayCell[][];
  todayIso: string;
  selectedIso: string;
  openings: Map<string, number>;
  shows: Show[];
  error: string | null;
  chipUrl: (changes: Record<string, string>) => string;
}) {
  const prev = addMonths(year, month, -1);
  const next = addMonths(year, month, 1);
  return (
    <>
      <section className="cal">
        <div className="cal-nav">
          <a
            className="cal-nav-btn"
            href={chipUrl({ cal: monthParam(prev.year, prev.month) })}
            aria-label="Previous month"
          >
            ‹
          </a>
          <h2 className="cal-month">{monthLabel(year, month)}</h2>
          <a
            className="cal-nav-btn"
            href={chipUrl({ cal: monthParam(next.year, next.month) })}
            aria-label="Next month"
          >
            ›
          </a>
        </div>
        <div className="cal-dow">
          {WEEKDAY_HEADERS.map((d) => (
            <div key={d} className="cal-dow-cell">
              {d}
            </div>
          ))}
        </div>
        <div className="cal-grid">
          {weeks.flat().map((cell) => {
            const count = openings.get(cell.iso) ?? 0;
            const cls = [
              'cal-cell',
              cell.inMonth ? '' : 'cal-cell--muted',
              cell.iso === todayIso ? 'cal-cell--today' : '',
              cell.iso === selectedIso ? 'cal-cell--selected' : '',
              count > 0 ? 'cal-cell--open' : '',
            ]
              .filter(Boolean)
              .join(' ');
            return (
              <a
                key={cell.iso}
                className={cls}
                href={chipUrl({
                  date: cell.iso,
                  cal: cell.iso.slice(0, 7),
                  view: 'calendar',
                })}
              >
                <span className="cal-cell-day">{cell.day}</span>
                {count > 0 && (
                  <span
                    className="cal-cell-count"
                    title={`${count} opening${count === 1 ? '' : 's'}`}
                  >
                    {count}
                  </span>
                )}
              </a>
            );
          })}
        </div>
      </section>

      <section className="list">
        <div className="list-head">
          <div className="list-head-mono">
            Shows running on {dayLabel(selectedIso)} ·{' '}
            {shows.length.toLocaleString()}
          </div>
        </div>
        {error ? (
          <p className="empty">Couldn&rsquo;t reach the database — {error}.</p>
        ) : shows.length === 0 ? (
          <p className="empty">
            Nothing listed for {dayLabel(selectedIso)}. Try another day.
          </p>
        ) : (
          <div className="row-list">
            {shows.map((s, i) => (
              <ShowRow key={s.id} idx={i + 1} show={s} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
