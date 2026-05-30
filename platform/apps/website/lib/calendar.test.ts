import { describe, expect, it } from 'vitest';
import {
  addMonths,
  dayLabel,
  monthGrid,
  monthLabel,
  monthParam,
  parseMonth,
} from './calendar';

const dowUtc = (iso: string) => {
  const y = Number(iso.slice(0, 4));
  const m = Number(iso.slice(5, 7));
  const d = Number(iso.slice(8, 10));
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay(); // 0=Sun..6=Sat
};

describe('monthGrid', () => {
  it('is always six weeks of seven days (42 cells)', () => {
    const g = monthGrid(2026, 6);
    expect(g).toHaveLength(6);
    expect(g.every((w) => w.length === 7)).toBe(true);
  });

  it('starts every row on a Monday', () => {
    const g = monthGrid(2026, 2);
    for (const week of g) {
      expect(dowUtc(week[0]!.iso)).toBe(1); // Monday
    }
  });

  it('lays out a month whose 1st is a Monday with no leading days', () => {
    // 1 June 2026 is a Monday.
    const g = monthGrid(2026, 6);
    expect(g[0]![0]).toEqual({ iso: '2026-06-01', day: 1, inMonth: true });
    expect(g[0]![6]!.iso).toBe('2026-06-07');
    // June has 30 days, then July spills into the last rows.
    expect(g[4]![1]).toEqual({ iso: '2026-06-30', day: 30, inMonth: true });
    expect(g[4]![2]).toEqual({ iso: '2026-07-01', day: 1, inMonth: false });
    expect(g[5]![6]!.iso).toBe('2026-07-12');
  });

  it('carries real adjacent-month dates as leading days (inMonth=false)', () => {
    // 1 July 2026 is a Wednesday → two leading days from June.
    const g = monthGrid(2026, 7);
    expect(g[0]![0]).toEqual({ iso: '2026-06-29', day: 29, inMonth: false });
    expect(g[0]![1]).toEqual({ iso: '2026-06-30', day: 30, inMonth: false });
    expect(g[0]![2]).toEqual({ iso: '2026-07-01', day: 1, inMonth: true });
  });
});

describe('addMonths', () => {
  it('wraps forward across the year boundary', () => {
    expect(addMonths(2026, 12, 1)).toEqual({ year: 2027, month: 1 });
  });
  it('wraps backward across the year boundary', () => {
    expect(addMonths(2026, 1, -1)).toEqual({ year: 2025, month: 12 });
  });
  it('is a no-op for delta 0', () => {
    expect(addMonths(2026, 6, 0)).toEqual({ year: 2026, month: 6 });
  });
});

describe('parseMonth', () => {
  it('parses a valid YYYY-MM', () => {
    expect(parseMonth('2026-08', '2026-06-15')).toEqual({ year: 2026, month: 8 });
  });
  it('falls back to the month of the fallback date', () => {
    expect(parseMonth(undefined, '2026-06-15')).toEqual({ year: 2026, month: 6 });
    expect(parseMonth('garbage', '2026-06-15')).toEqual({ year: 2026, month: 6 });
  });
  it('rejects out-of-range months', () => {
    expect(parseMonth('2026-13', '2026-06-15')).toEqual({ year: 2026, month: 6 });
  });
});

describe('labels', () => {
  it('monthLabel is long-form', () => {
    expect(monthLabel(2026, 6)).toBe('June 2026');
  });
  it('monthParam is YYYY-MM', () => {
    expect(monthParam(2026, 6)).toBe('2026-06');
  });
  it('dayLabel names the weekday', () => {
    expect(dayLabel('2026-06-01')).toBe('Mon 1 Jun 2026');
    expect(dayLabel('2026-06-15')).toBe('Mon 15 Jun 2026');
  });
});
