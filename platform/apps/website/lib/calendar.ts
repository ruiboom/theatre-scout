/**
 * Pure month-grid helpers for the /shows calendar view.
 *
 * No `Date.now()` or argless `new Date()` — "today" is injected by the caller
 * (see lib/time.londonToday) so these stay deterministic and unit-testable. Every
 * Date instance is built and read through UTC accessors only, so a grid never
 * shifts by a day with the host timezone.
 */

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
] as const;

const MONTHS_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
] as const;

const WEEKDAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;

/** Monday-first weekday headers for the grid. */
export const WEEKDAY_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

/** A year + 1-based month (1 = January, 12 = December). */
export type YearMonth = { year: number; month: number };

export type DayCell = {
  iso: string; // YYYY-MM-DD
  day: number; // 1–31
  inMonth: boolean; // false for the leading/trailing days of adjacent months
};

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function isoOf(year: number, month: number, day: number): string {
  return `${year}-${pad2(month)}-${pad2(day)}`;
}

/**
 * A 6×7 calendar grid (always 42 cells, six weeks) for the given month,
 * Monday-first. Leading and trailing cells carry the real adjacent-month dates
 * with `inMonth: false` so they can be rendered muted but still navigable.
 */
export function monthGrid(year: number, month: number): DayCell[][] {
  const first = new Date(Date.UTC(year, month - 1, 1));
  // getUTCDay: 0=Sun..6=Sat → Monday-first lead (Mon=0 … Sun=6).
  const lead = (first.getUTCDay() + 6) % 7;
  const start = new Date(Date.UTC(year, month - 1, 1 - lead));

  const weeks: DayCell[][] = [];
  for (let w = 0; w < 6; w++) {
    const row: DayCell[] = [];
    for (let d = 0; d < 7; d++) {
      const cur = new Date(start);
      cur.setUTCDate(start.getUTCDate() + w * 7 + d);
      row.push({
        iso: isoOf(cur.getUTCFullYear(), cur.getUTCMonth() + 1, cur.getUTCDate()),
        day: cur.getUTCDate(),
        inMonth: cur.getUTCMonth() === month - 1,
      });
    }
    weeks.push(row);
  }
  return weeks;
}

/** Shift a {year, month} by a whole number of months, wrapping the year. */
export function addMonths(year: number, month: number, delta: number): YearMonth {
  const total = year * 12 + (month - 1) + delta;
  const y = Math.floor(total / 12);
  return { year: y, month: total - y * 12 + 1 };
}

/**
 * Resolve the `cal=YYYY-MM` param to a concrete month, falling back to the month
 * of `fallbackIso` (a YYYY-MM-DD — the selected date, or today). Out-of-range
 * months (e.g. `2026-13`) fall back too.
 */
export function parseMonth(cal: string | undefined, fallbackIso: string): YearMonth {
  const fb = { year: Number(fallbackIso.slice(0, 4)), month: Number(fallbackIso.slice(5, 7)) };
  if (!cal || !/^\d{4}-\d{2}$/.test(cal)) return fb;
  const year = Number(cal.slice(0, 4));
  const month = Number(cal.slice(5, 7));
  if (month < 1 || month > 12) return fb;
  return { year, month };
}

/** "YYYY-MM" — for building `cal=` navigation links. */
export function monthParam(year: number, month: number): string {
  return `${year}-${pad2(month)}`;
}

/** "June 2026" — the calendar header. */
export function monthLabel(year: number, month: number): string {
  return `${MONTHS[month - 1]} ${year}`;
}

/** "Mon 15 Jun 2026" — the selected-day heading. Pure and timezone-immune. */
export function dayLabel(iso: string): string {
  const y = Number(iso.slice(0, 4));
  const mo = Number(iso.slice(5, 7));
  const d = Number(iso.slice(8, 10));
  const dow = new Date(Date.UTC(y, mo - 1, d)).getUTCDay();
  return `${WEEKDAYS_SHORT[dow]} ${d} ${MONTHS_SHORT[mo - 1]} ${y}`;
}
