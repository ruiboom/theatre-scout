# Platform — high-level TODO

Picking up the multi-surface platform later. The bootstrap lives in [`platform/`](platform/) — full architecture, six MCP tools, schema, scrapers, seed data — but nothing has been run yet.

This is the milestone-level view. Step-by-step commands are in [`platform/SETUP.md`](platform/SETUP.md) (local) and [`platform/DEPLOY.md`](platform/DEPLOY.md) (online).

> **Where this fits.** Per [`platform/docs/BUILD_PLAN.md`](platform/docs/BUILD_PLAN.md): the current `scout/` site is Phase 1 (ship the website, soft-launch ~1 Sept 2026). The `platform/` work is Phase 2 (Sept–Oct 2026: port to multi-surface, build the MCP server) and Phase 3 (Oct/Nov: AI-native launch moment).

---

## Phase A — run the platform locally

- [x] Install prerequisites: Node 20, pnpm, uv, Docker (or OrbStack)
- [x] `pnpm install` in `platform/`
- [x] Boot Postgres + PostGIS via Docker (`postgis/postgis:16-3.4`, port 5433 if 5432 is taken)
- [x] Apply `packages/db/schema.sql` and `scripts/seed.sql` to the local DB
- [x] `cp .env.example .env` and copy to `apps/website/.env.local`
- [x] `pnpm --filter website dev` → homepage renders 6 seeded shows on :3000
- [x] Smoke-test all six API endpoints (`/api/v1/shows`, `/whats-on`, `/recommend`, etc.)
- [x] Wire up Python scrapers (`uv sync --extra dev`, run `scrape venue example`) — `scrape_runs` row written
- [x] `pnpm --filter mcp-server dev` → `:8787/health` returns ok; initialize + tools/list + tools/call all green
- [x] `pnpm test` (21 tests) and `uv run pytest` (15 tests) both green
- [ ] Connect Claude Desktop via `mcp-remote`, confirm the six tools are callable *(local-machine step — see [`platform/SETUP.md`](platform/SETUP.md) §9)*

## Phase B — deploy online

- [x] Push the repo to GitHub (`ruiboom/theatre-scout`, public)
- [x] Create a Neon project (London region), enable PostGIS, copy pooled + direct URLs
- [x] Apply `schema.sql` to Neon (current schema with `0002_align_with_scout` columns)
- [x] Import to Vercel — root directory `platform/apps/website`, `DATABASE_URL` = pooled URL → live at <https://theatre-scout-zunz.vercel.app>
- [x] Verify the live site + `/api/v1/whats-on` from a browser
- [x] `wrangler login`, set `API_BASE_URL` secret to the Vercel URL, `wrangler deploy` the MCP server → live at <https://platform-mcp-server.boomclick.workers.dev/mcp>
- [x] Confirm `/health` and the MCP `initialize` handshake on the deployed Workers URL
- [x] Add `.github/workflows/scrape.yml` daily cron (05:00 UTC) + `NEON_DATABASE_URL` secret + `SITE_BASE_URL` variable for the smoke test
- [x] Trigger the workflow once manually — fresh runs land ~789 shows on Neon, smoke-test passes
- [x] Port `scout/` adapters into `platform/apps/scrapers/` (32 bespoke + 36 GenericAdapter via bulk = 68 venues). Workflow now runs platform's scrapers direct to Neon — no SQLite bridge.
- [x] Repoint Claude Desktop config to `https://platform-mcp-server.boomclick.workers.dev/mcp`
- [ ] (Optional) Custom domain on Vercel + a `mcp.…` subdomain on Cloudflare

## Phase C — known follow-ups (don't block on these)

- [x] *(done — see Phase B)* Port `scout/` adapters into `platform/apps/scrapers/`
- [x] **Fix `open-air-theatre` adapter — inconsistent dates.** Bespoke parser walks `article.ProductionTeaser` cards, lifts the year from each `Section-divide-title` heading, and parses `02 May` / `02 May – 06 June` ranges. 10/10 shows now have `start_date` (vs. 0/10 with the generic selector).
- [x] **Live venue map widget on `/venues/[slug]`** — `<VenueMap>` client component lazy-loads Leaflet, OSM tiles, square ink marker. Coordinates come from PostGIS `venues.location`.
- [x] **OpenAPI spec at `/api/openapi`** — hand-rolled OpenAPI 3.1 covering all six endpoints. CORS-open, cached 1h. Custom GPT setup: paste that URL as the action import. (MCP worker's `/openapi.json` now 302s to it.)
- [x] **Admin dashboard at `/admin`** — single-password gate (`ADMIN_PASSWORD` env), HTTP-only cookie sessions, server-action login. Dashboard shows visit totals (24h / 7d / 30d), top searches, top venue-page visits, top outbound show clicks, scrape status, and a "Refresh data" button that dispatches the daily-scrape workflow via the GitHub API. **Requires two new env vars on Vercel: `ADMIN_PASSWORD` (any string) and `GITHUB_TOKEN` (fine-grained PAT with `Actions: read & write` on `ruiboom/theatre-scout`).**
- [ ] **Refine the admin dashboard.** v0 lands the foundation (events table, server-side visit/search tracking, `/r` outbound redirect, dashboard, refresh trigger). Future work: per-day timeseries chart, geo aggregation by venue cluster, retention proxy via `ip_prefix`.
- [ ] **User wish-lists** — let visitors mark shows they want to see; hand-roll a tiny "your list" surface with localStorage by default, optional email magic-link to persist server-side. Hooks into the `/shows` row design (a small ★ in the row gutter would fit cleanly).
- [ ] **Standalone platform — drop the `scout/` dependency.** `platform/` now scrapes directly to Neon, but the repo still treats `scout/` as the live site. Eventually: extract `platform/` to its own repo (or just delete `scout/` once it's clear nothing references it). The remaining ties: `theatres.yaml` and `theatre-coords.yaml` at the repo root (can be moved into `platform/data/`), and the `scout/` site itself if it's still serving anyone (kill once Vercel parity is clear).
- [ ] "New" filter chip on `/shows` should query `first_seen_at` directly (currently falls back to recent ordering) — *folded into **Phase D / D3** below.*
- [ ] Replace the rule-based recommender in `apps/website/lib/recommend.ts` with an Anthropic call once the tag taxonomy is rich enough
- [ ] Email integration (Beehiiv or Buttondown) — pull "new this week" via the API on a cron
- [ ] Social bot (Buffer + Make.com) — post new listings, throttled
- [ ] Admin CMS — manual show entry / corrections (different scope from the analytics dashboard above)
- [x] Pick a real name — landed on **Theatre Scout** (May 2026). Display strings, MCP server name, scraper User-Agent and docs all updated. The shortlist + rationale is preserved in [`platform/docs/POSITIONING.md`](platform/docs/POSITIONING.md) for reference.

---

## Phase D — new features: Punt · Health · Feeds

Three additive features speced May 2026. Independent of each other; the
recommended build order is the numbering below (fast + visible → protect the
data → biggest surface). Full file-by-file sequencing in
[`platform/docs/FEATURE_BUILD_PLAN.md`](platform/docs/FEATURE_BUILD_PLAN.md).

### D1 — Tonight's Punt + Punt Roulette · ~½ day · no schema/API change

"Take a punt" made literal: one random show from a constrained pool, presented big.

- [ ] `apps/website/lib/random.ts` *(new)* — lift `sampleRandom` out of `app/shows/page.tsx`; add a seeded `pickOne(arr, seed)` (mulberry32) so a punt URL is shareable and **Spin again** is deterministic.
- [ ] `apps/website/app/punt/page.tsx` *(new, `force-dynamic`)* — build the pool via `searchShows` (Tonight = `londonToday()`; This weekend = `resolveWindow('this_weekend')`; optional `max_price`); **post-filter** to shows whose run genuinely covers the date (drop `start_date IS NULL` — `searchShows` includes them on purpose); pick one; render with the `show-hero` / `show-still` / `spec` classes; budget + window chips; **Book ↗** (`trackedExternalHref`), **Spin again ↻** (`?s=seed+1`), **See all tonight →** (`/shows?when=today`).
- [ ] `apps/website/app/page.tsx` — add a `Take a punt ▶` CTA in `.hero-cta`.
- **Acceptance:** `/punt`, `/punt?max_price=15`, `/punt?when=weekend` each return one on-brand pick; `?s=N` is stable on reload while Spin again re-rolls; an empty pool shows a "widen your punt" fallback, not a dead end.

### D2 — Scraper health monitor · ~1 day · catches silent adapter rot

The daily smoke test only checks the **global** total (`> 100`); a single venue dropping to 0 shows after a site redesign passes unnoticed (the run still records `status='success', shows_found=0`). This flags per-venue rot.

- [ ] `packages/db/migrations/0004_venue_health_view.sql` *(new)* — `CREATE VIEW venue_health` over `scrape_runs`: flag the latest run when it is `failed`, `silent-zero` (0 found vs a non-trivial 21-day baseline), `collapse` (< 30 % of median, baseline ≥ 5), or `stale` (no run > 30h). One source of truth for both consumers below; mirror into `schema.sql`; apply to local + Neon.
- [ ] `apps/scrapers/scrapers/health.py` *(new)* + `scrape health` command (`cli.py`) — `SELECT * FROM venue_health`; table + `--json`; **exit 1 if any flagged**. Reuses `writer._conn()`.
- [ ] `.github/workflows/scrape.yml` — add `issues: write`; run `scrape health --json` (non-failing) after the scrape; an `actions/github-script` step maintains **one rolling, self-closing issue** (label `scraper-health`) via the built-in `GITHUB_TOKEN` (no PAT needed).
- [ ] `apps/website/lib/queries/events.ts::venueHealth()` + a "Venue health" panel on `app/admin/page.tsx` (reuse `RankedList`; red = failed/zero, amber = collapse/stale; empty = "all healthy ✓").
- **Acceptance:** synthetic `scrape_runs` (healthy history + a latest zero) makes `scrape health` flag exactly that venue and exit 1; the rolling issue opens on anomaly and closes when clear; `/admin` shows the panel.

### D3 — Just Announced / Closing Soon · ~1 day · filter chips + editorial pages

Turns the daily diff into product. Supersedes the "New chip → `first_seen_at`" follow-up in Phase C.

- [ ] `packages/shared/src/schemas.ts` — add `first_seen_within_days`, `closing_within_days`; extend `WhenChip` with `'closing'`; add `'first_seen'` to the `sort` enum. (MCP `search_shows` inherits the new params.)
- [ ] `apps/website/lib/queries/shows.ts` — wire both filters into `searchShows`; add `first_seen` to `orderByFor`; add `recentlyAdded(days, limit)` (selects `first_seen_at` for the "added Nd ago" badge) and `closingSoon(days, limit)`.
- [ ] `apps/website/app/shows/page.tsx` — replace the **stubbed** `when='new'` branch (currently a fake wide window) with `first_seen_within_days: 14`; add a `when='closing'` branch (`closing_within_days: 14`, sort `end_date`); add a **Closing soon** chip beside **New**.
- [ ] `apps/website/components/editorial-feed.tsx` *(new)* + `app/new/page.tsx` + `app/closing/page.tsx` *(new)* — magazine layout: big art, kicker, large tracked title, dates + price, **visible `description_short`**, and a "New · added Nd ago" / "Closes in N days" badge. ~30 lines of `.feature*` CSS in `app/style.css`.
- **Acceptance:** a show added today appears in `/new` and drops out after 14d; `/closing` excludes open-ended and already-past runs; `/shows?when=new|closing` chips work; descriptions + badges render; missing images degrade gracefully.

---

## What's already done in the bootstrap

For reference when you come back — artefacts in [`platform/`](platform/):

- Monorepo: pnpm workspaces + turbo
- `packages/shared` — types + zod schemas (the contract between every surface), aligned with scout's `Show` shape (image_url, start_date, end_date, show_type, venue category)
- `packages/db` — Postgres schema with PostGIS + tsvector FTS; migration `0002_align_with_scout.sql` adds shows.start_date/end_date and venues.postcode_prefix
- `apps/website` — Next.js 15, six API routes with real SQL queries, **Swiss Index UI** (design-guide CSS imported byte-for-byte), home venue index, `/shows` rails+list with Today/This week/New chips + sort + filters, `/venues/[slug]` programme view
- `apps/mcp-server` — TS MCP on Cloudflare Workers, six tools wired to the API via `agents/mcp`
- `apps/scrapers` — **Scrapling-based** ingestion mirroring scout's Tier 3: `FetcherSession` + `StealthySession` with dedicated browser thread, 3-phase orchestrator (serial listings → parallel enrich with round-robin → serial writes), per-adapter `enrich()` hook, GenericAdapter + `bulk.py`, `classify.py`, JSON-LD + date-range helpers — adapter API is byte-identical to scout's so existing adapters port mechanically
- `scripts/seed.sql` — 3 venues with postcodes, 6 shows with start_date/end_date, performances
- `docs/` — copies of architecture, tool surface, build plan, positioning, audience strategy
