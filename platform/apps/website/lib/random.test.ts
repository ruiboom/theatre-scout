import { describe, expect, it } from 'vitest';
import { hourlySeed, pickOne, sampleSeeded } from './random';

describe('pickOne', () => {
  const pool = ['a', 'b', 'c', 'd', 'e'];

  it('is deterministic for a given seed (shareable /punt?s=N)', () => {
    expect(pickOne(pool, 3)).toBe(pickOne(pool, 3));
    expect(pickOne(pool, 42)).toBe(pickOne(pool, 42));
  });

  it('returns null for an empty pool', () => {
    expect(pickOne([], 1)).toBeNull();
  });

  it('always returns a member of the pool', () => {
    for (let s = 1; s <= 50; s++) expect(pool).toContain(pickOne(pool, s));
  });

  it('Spin again (consecutive seeds) never repeats until the pool is exhausted', () => {
    const cycle = Array.from({ length: pool.length }, (_, i) => pickOne(pool, i + 1));
    expect(new Set(cycle).size).toBe(pool.length); // one full cycle = all distinct
    expect(pickOne(pool, pool.length + 1)).toBe(pickOne(pool, 1)); // then wraps
  });

  it('handles a single-item pool (every spin is the only show)', () => {
    expect(pickOne(['only'], 1)).toBe('only');
    expect(pickOne(['only'], 9)).toBe('only');
  });
});

describe('sampleSeeded', () => {
  const pool = ['a', 'b', 'c', 'd', 'e', 'f', 'g'];

  it('is deterministic for a given seed (so the ISR /shows render is stable)', () => {
    expect(sampleSeeded(pool, 3, 7)).toEqual(sampleSeeded(pool, 3, 7));
  });

  it('varies with the seed', () => {
    const seen = new Set(
      Array.from({ length: 10 }, (_, s) => sampleSeeded(pool, 3, s).join()),
    );
    expect(seen.size).toBeGreaterThan(1);
  });

  it('never repeats an item and caps at the pool size', () => {
    const picks = sampleSeeded(pool, 20, 1);
    expect(picks).toHaveLength(pool.length);
    expect(new Set(picks).size).toBe(pool.length);
    expect(sampleSeeded([], 3, 1)).toEqual([]);
  });
});

describe('hourlySeed', () => {
  it('is constant within an hour and changes across it', () => {
    const t = Date.UTC(2026, 8, 4, 10, 15);
    expect(hourlySeed(t)).toBe(hourlySeed(t + 30 * 60_000));
    expect(hourlySeed(t)).not.toBe(hourlySeed(t + 60 * 60_000));
  });
});
