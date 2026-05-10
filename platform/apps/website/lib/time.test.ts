import { describe, expect, it } from 'vitest';
import { resolveWindow } from './time';

describe('resolveWindow', () => {
  it('"tonight" returns a single-day window', () => {
    const w = resolveWindow('tonight');
    expect(w.from).toEqual(w.to);
    expect(w.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('"tomorrow" is one day after tonight', () => {
    const t = resolveWindow('tonight');
    const tm = resolveWindow('tomorrow');
    const d1 = new Date(t.from + 'T00:00:00Z').getTime();
    const d2 = new Date(tm.from + 'T00:00:00Z').getTime();
    expect(d2 - d1).toBe(86_400_000);
  });

  it('"this_weekend" spans 3 days (Fri–Sun)', () => {
    const w = resolveWindow('this_weekend');
    const d1 = new Date(w.from + 'T00:00:00Z').getTime();
    const d2 = new Date(w.to + 'T00:00:00Z').getTime();
    expect(d2 - d1).toBe(2 * 86_400_000);
  });

  it('"next_weekend" is exactly 7 days after this_weekend', () => {
    const t = resolveWindow('this_weekend');
    const n = resolveWindow('next_weekend');
    const d1 = new Date(t.from + 'T00:00:00Z').getTime();
    const d2 = new Date(n.from + 'T00:00:00Z').getTime();
    expect(d2 - d1).toBe(7 * 86_400_000);
  });
});
