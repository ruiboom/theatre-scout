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
- [ ] "New" filter chip on `/shows` should query `first_seen_at` directly (currently falls back to recent ordering)
- [ ] Replace the rule-based recommender in `apps/website/lib/recommend.ts` with an Anthropic call once the tag taxonomy is rich enough
- [ ] Email integration (Beehiiv or Buttondown) — pull "new this week" via the API on a cron
- [ ] Social bot (Buffer + Make.com) — post new listings, throttled
- [ ] Admin CMS — manual show entry / corrections (different scope from the analytics dashboard above)
- [x] Pick a real name — landed on **Theatre Scout** (May 2026). Display strings, MCP server name, scraper User-Agent and docs all updated. The shortlist + rationale is preserved in [`platform/docs/POSITIONING.md`](platform/docs/POSITIONING.md) for reference.

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
