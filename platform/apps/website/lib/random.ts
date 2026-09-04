/**
 * Random helpers shared across pages.
 *
 * `sampleRandom` is the unseeded shuffle-and-take. `sampleSeeded` is its
 * deterministic sibling, used by the /shows rails with an hourly seed so the
 * render is stable within the hour (and therefore CDN-cacheable) while still
 * rotating through the day. `pickOne` is seeded (mulberry32) so a result is
 * reproducible from a URL: the /punt page uses it so a punt link is shareable
 * and "Spin again" is just the next seed.
 */

/** Pick up to `n` random items from `arr` (unseeded; uses Math.random). */
export function sampleRandom<T>(arr: T[], n: number): T[] {
  const copy = [...arr];
  const take = Math.min(n, copy.length);
  for (let i = 0; i < take; i++) {
    const j = i + Math.floor(Math.random() * (copy.length - i));
    [copy[i], copy[j]] = [copy[j]!, copy[i]!];
  }
  return copy.slice(0, take);
}

/**
 * Pick up to `n` items from `arr`, deterministically for a given `seed`.
 * Same input + same seed → same picks, so a page using it can be cached.
 */
export function sampleSeeded<T>(arr: T[], n: number, seed: number): T[] {
  const take = Math.min(n, arr.length);
  const order = shuffledIndices(arr.length, seed);
  return order.slice(0, take).map((i) => arr[i]!);
}

/** Seed that changes once an hour — what the /shows rails rotate on. */
export function hourlySeed(now: number = Date.now()): number {
  return Math.floor(now / 3_600_000);
}

/** Deterministic PRNG (mulberry32). Same seed → same sequence. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Mix an integer for use as a PRNG seed (decorrelates small inputs). */
function hashSeed(n: number): number {
  let h = n >>> 0;
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
  return (h ^ (h >>> 16)) >>> 0;
}

/** Deterministic Fisher–Yates shuffle of [0..n-1], seeded so it's stable. */
function shuffledIndices(n: number, seed: number): number[] {
  const rng = mulberry32(hashSeed(seed));
  const idx = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [idx[i], idx[j]] = [idx[j]!, idx[i]!];
  }
  return idx;
}

/**
 * Pick one item by walking a fixed shuffle of `arr`. `seed` is the 1-based
 * position in that shuffle, so consecutive seeds — what "Spin again" produces —
 * always return a DIFFERENT item, cycling through the whole pool before
 * repeating, while any given `/punt?s=N` stays stable (shareable). The shuffle
 * is keyed to the pool size so it doesn't reshuffle mid-spin.
 */
export function pickOne<T>(arr: T[], seed: number): T | null {
  if (arr.length === 0) return null;
  const order = shuffledIndices(arr.length, arr.length);
  const pos = (((seed - 1) % arr.length) + arr.length) % arr.length;
  return arr[order[pos]!] ?? null;
}
