import { describe, expect, it } from 'vitest';
import { pickOne } from './random';

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
