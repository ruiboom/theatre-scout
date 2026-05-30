# Feature build plan — Punt · Health · Feeds

Sequenced execution plan for the three features speced in
[`PLATFORM_TODO.md` § Phase D](../../PLATFORM_TODO.md). Each is **independent and
additive** — no feature blocks another — but the recommended order below
maximises momentum and de-risks the data the later features display.

All three target the hosted platform: `apps/website` (Next.js), `apps/scrapers`
(Python), `packages/db`, `packages/shared`.

---

## Order & rationale

| # | Feature | Effort | Why this slot |
|---|---------|--------|---------------|
| 1 | Tonight's Punt + Roulette | ~½ day | Fast, visible, on-brand. **Zero** schema/API change — a pure new page. Proves the design-system reuse and gives an immediate demo surface. |
| 2 | Scraper health monitor | ~1 day | Mostly backend. Protects the data integrity that #1 and #3 display — ship it before the feeds lean harder on freshness. Introduces the `venue_health` view. |
| 3 | Just Announced / Closing Soon | ~1 day | Largest surface area (shared query params + sort + two pages + component + CSS). Benefits from patterns settled in #1/#2 and from a healthy daily scrape feeding `first_seen_at`. |

Total ≈ 2.5 focused days. **One PR per feature** (repo convention: small, focused
commits; one logical change per PR).

---

## Shared conventions (apply to all three)

- **Additive only.** New params / pages / queries; don't change the existing
  `Show` shape, existing routes, or the six MCP tool *signatures*. New *optional*
  params are fine — the sanctioned extension path in `docs/TOOL_SURFACE.md`.
- **`force-dynamic`** on every new page (matches every existing route — fresh DB
  reads, no ISR).
- **DB access only via `apps/website/lib/queries/*`** in the website; CI and the
  scrapers use `writer._conn()`. The MCP server never touches the DB.
- **Track new pages** with `trackEvent({ type: 'visit', … })` and use
  `trackedExternalHref()` on outbound booking links, so new surfaces appear in
  `/admin` analytics.
- **Reuse the Swiss-Index classes** (`hero`, `show-hero`, `card`, `row`,
  `ts-chip`, `ts-btn`, `rail`, `spec`, …) before inventing CSS.
- **Green gates before each PR:** `pnpm -w build` (Vercel's strict TS build) +
  `pnpm -w test` + ESLint/Prettier for TS; `uv run ruff format . && uv run ruff
  check . && uv run pytest` in `apps/scrapers`.
- **No new secrets.** Punt and Feeds need none; Health uses the workflow's
  built-in `GITHUB_TOKEN` (distinct from the Vercel admin PAT used by the
  Refresh button).

---

## Milestone 1 — Tonight's Punt (~½ day)

Goal & acceptance criteria: [`PLATFORM_TODO.md` § D1](../../PLATFORM_TODO.md).

1. **`apps/website/lib/random.ts`** *(new)* — lift `sampleRandom<T>` out of
   `app/shows/page.tsx` and add `pickOne<T>(arr, seed?)` backed by a seeded
   `mulberry32`. Re-point `shows/page.tsx` at the import (no behaviour change
   there). *Done when:* a small `random.test.ts` proves same-seed → same pick.
2. **`apps/website/app/punt/page.tsx`** *(new, `force-dynamic`)*:
   - read `?when` (`tonight` | `weekend`, default tonight), `?max_price`, `?s` (seed);
   - window: tonight → `londonToday()`; weekend → `resolveWindow('this_weekend')`;
   - pool: `searchShows({ date_from, date_to, max_price, min_price: 0, limit: 200 })`;
   - **post-filter the pool** — drop `start_date == null` and require the run to
     actually cover the window. (`searchShows` deliberately *includes*
     null-date shows, `lib/queries/shows.ts` lines ~150–164; for a punt that's
     wrong.)
   - `pickOne(pool, seed)`; render with `show-hero` / `show-l` / `show-r` /
     `show-still` / `show-title` / `spec` / `ts-btn`; budget + window chips
     (existing `Chip` pattern);
   - actions: **Book ↗** (`trackedExternalHref`), **Spin again ↻**
     (`/punt?…&s=${seed + 1}`), **See all tonight →** (`/shows?when=today`);
   - empty pool → "No punts under £X tonight — try [Any price] / [This weekend]"
     (links), never a dead end.
3. **`apps/website/app/page.tsx`** — add a secondary **Take a punt ▶** button in
   `.hero-cta` (primary stays "Browse the index").
4. **Ship** — manual pass over the D1 acceptance list → PR
   `feat(platform): Tonight's Punt`.

---

## Milestone 2 — Scraper health monitor (~1 day)

Goal & acceptance criteria: [`PLATFORM_TODO.md` § D2](../../PLATFORM_TODO.md).

1. **`packages/db/migrations/0004_venue_health_view.sql`** *(new)* — `CREATE VIEW
   venue_health` over `scrape_runs` (DISTINCT ON latest run per venue + a 21-day
   success baseline; flag `failed` / `silent-zero` / `collapse` / `stale`). Also
   add the view to the canonical `packages/db/schema.sql`. Apply to local **and**
   Neon via the repo's migration path (`packages/db/scripts/migrate.mjs`, or
   `psql -f`). *Done when:* `SELECT * FROM venue_health` runs on both.
2. **`apps/scrapers/scrapers/health.py`** *(new)* + a **`scrape health`** command
   in `cli.py` — `SELECT * FROM venue_health` via `writer._conn()`; pretty table
   + `--json`; `--max-stale-hours` / `--min-baseline` overrides; **exit 1 if any
   venue is flagged**. *Done when:* a test seeds synthetic `scrape_runs` (healthy
   history + a latest zero) and asserts that venue is flagged and exit code is 1.
3. **`.github/workflows/scrape.yml`** — add `issues: write` to `permissions`
   (currently `contents: read`); after the scrape step run a non-failing
   `uv run scrape health --json > health.json || true`, then an
   `actions/github-script@v7` step that maintains **one rolling issue** (label
   `scraper-health`): create on first anomaly, update + comment while it
   persists, close with "all healthy ✓" when clear. Built-in `GITHUB_TOKEN` only.
4. **`apps/website/lib/queries/events.ts::venueHealth()`** + a **"Venue health"**
   panel on **`app/admin/page.tsx`** (reuse `RankedList`; red = failed / zero,
   amber = collapse / stale; link names to `/venues/<slug>`; empty = "All venues
   healthy ✓").
5. **Ship** — synthetic-data test green; dry-run the github-script branch logic;
   `/admin` panel renders → PR `feat(platform): scraper health monitor`.

> **Watch:** the baseline guards (`max_found ≥ 1`, `median ≥ 5`) suppress false
> alarms on brand-new and legitimately-dark venues. Tune thresholds against a
> week of real `scrape_runs` before fully trusting the auto-issue.

---

## Milestone 3 — Just Announced / Closing Soon (~1 day)

Goal & acceptance criteria: [`PLATFORM_TODO.md` § D3](../../PLATFORM_TODO.md).
Closes the existing "New chip → `first_seen_at`" follow-up.

1. **`packages/shared/src/schemas.ts`** — add optional `first_seen_within_days`
   and `closing_within_days`; extend `WhenChip` → `['today','week','new','closing']`;
   add `'first_seen'` to the `sort` enum. Update `schemas.test.ts`.
2. **`apps/website/lib/queries/shows.ts`** — add the two filter clauses to the
   `filters` block in `searchShows`; add a `first_seen` case to `orderByFor`
   (`s.first_seen_at DESC NULLS LAST`); add `recentlyAdded(days, limit)` (selects
   an extra `s.first_seen_at` for the badge; returns `Show & { first_seen_at }`)
   and a thin `closingSoon(days, limit)` wrapper.
3. **`apps/website/app/shows/page.tsx`** — replace the **stubbed** `when === 'new'`
   branch (the fake `+365`-day window, lines ~130–135) with
   `first_seen_within_days: 14`; add a `when === 'closing'` branch
   (`closing_within_days: 14`, sort `end_date`); default `new` sort → `first_seen`;
   add a **Closing soon** `Chip` beside **New** in `.controls-l .tabs`.
4. **`apps/website/components/editorial-feed.tsx`** *(new)* +
   **`app/new/page.tsx`** + **`app/closing/page.tsx`** *(new, `force-dynamic`)* —
   shared magazine layout: big art (graceful placeholder when `image_url` is
   null), kicker (`type · venue · neighbourhood`), large tracked title, dates +
   price, **visible `description_short`** (hidden when empty), and a badge:
   "New · added {fmtRelative(first_seen_at)}" / "Closes in N days". ~30 lines of
   `.feature*` CSS in `app/style.css`.
5. **Cross-link** — each editorial page header → "See all in the index →"
   (`/shows?when=new` | `?when=closing`); optionally a "Just announced" rail on
   `/shows`.
6. **Ship** — D3 acceptance list; flip the corresponding Phase C item to done in
   `PLATFORM_TODO.md` → PR `feat(platform): Just Announced & Closing Soon`.

---

## Definition of done (all three)

- [ ] Three PRs merged, each green on build + tests + lint/format/types.
- [ ] `/punt`, `/new`, `/closing` live and tracked; `/shows` gains **New** +
      **Closing soon** chips wired to real `first_seen_at` / `end_date` queries.
- [ ] `venue_health` view live on Neon; `scrape health` runs in the daily
      workflow; rolling health issue + `/admin` panel both working.
- [ ] No new env vars; the built-in workflow `GITHUB_TOKEN` is the only new
      permission grant.
- [ ] PLATFORM_TODO § Phase D items checked; the legacy "New chip" follow-up closed.
