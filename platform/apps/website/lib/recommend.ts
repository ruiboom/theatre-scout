import type { Show, Recommendation } from '@platform/shared';
import type { RecommendShowsInput } from '@platform/shared';
import { searchShows } from './queries/shows';

/**
 * Vibe-string → recommended shows, with a generated `why` per result.
 *
 * Phase 1: rule-based. Token-overlap between the vibe string and each show's
 *   genre + tag slugs. Cheap, deterministic, easy to test.
 *
 * Phase 2 (after launch): hand off `vibe` to a small LLM that returns ranked
 *   show ids + a `why` per pick. The Internal API stays the only place this
 *   logic lives — every surface gets the same answer.
 *
 * The contract is unchanged either way: `{ recommendations: [{ show, why }] }`.
 */

function tokenize(s: string): Set<string> {
  return new Set(
    s
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 2),
  );
}

function score(vibeTokens: Set<string>, show: Show): number {
  const haystack = new Set<string>([
    ...show.genres,
    ...show.tags,
    show.show_type,
    ...tokenize(show.title),
    ...tokenize(show.description_short),
  ]);
  let s = 0;
  for (const t of vibeTokens) if (haystack.has(t)) s += 1;
  // tiny boost for cheap shows when the vibe mentions "cheap" / "broke"
  if (
    (vibeTokens.has('cheap') || vibeTokens.has('broke')) &&
    show.price_max != null &&
    show.price_max > 0 &&
    show.price_max <= 15
  ) {
    s += 1;
  }
  return s;
}

function buildWhy(vibe: string, show: Show, matched: string[]): string {
  if (matched.length === 0) {
    return `It's a ${show.genres[0] ?? 'show'} at ${show.venue.name} — closest match in the current programme.`;
  }
  const venuePhrase = `at ${show.venue.name} in ${show.venue.neighbourhood}`;
  const matchPhrase =
    matched.length === 1
      ? `tagged ${matched[0]}`
      : `tagged ${matched.slice(0, 2).join(' and ')}`;
  return `${matchPhrase} — fits "${vibe}", playing ${venuePhrase}.`;
}

export async function recommendShows(
  input: RecommendShowsInput,
): Promise<{ recommendations: Recommendation[] }> {
  const limit = input.limit ?? 5;

  // Pull a wider candidate pool — recommendations rank, they don't filter.
  const { shows: candidates } = await searchShows({
    date_from: input.constraints?.date_from,
    date_to: input.constraints?.date_to,
    max_price: input.constraints?.max_price,
    neighbourhood: input.constraints?.neighbourhood,
    near: input.constraints?.near,
    limit: 50,
    min_price: 0,
  });

  const vibeTokens = tokenize(input.vibe);
  const exclude = new Set((input.exclude_genres ?? []).map((g) => g.toLowerCase()));

  const ranked = candidates
    .filter((s) => !s.genres.some((g) => exclude.has(g.toLowerCase())))
    .map((s) => {
      const matched = [...s.genres, ...s.tags].filter((t) => vibeTokens.has(t));
      return { show: s, score: score(vibeTokens, s), matched };
    })
    .filter((r) => r.score > 0 || candidates.length < limit)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return {
    recommendations: ranked.map(({ show, matched }) => ({
      show,
      why: buildWhy(input.vibe, show, matched),
    })),
  };
}
