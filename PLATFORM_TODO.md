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

- [ ] Push the repo to GitHub (this branch + main)
- [ ] Create a Neon project (London region), enable PostGIS, copy pooled + direct URLs
- [ ] Apply `schema.sql` (and optionally `seed.sql`) to the hosted DB
- [ ] Import to Vercel: root directory `platform/apps/website`, env var `DATABASE_URL = <pooled>`
- [ ] Verify the live site + `/api/v1/whats-on` from a browser
- [ ] `wrangler login`, set `API_BASE_URL` secret to the Vercel URL, `wrangler deploy` the MCP server
- [ ] Confirm `/health` and `/mcp` on the deployed Workers URL
- [ ] Add `.github/workflows/scrape.yml` cron + `DATABASE_URL_DIRECT` repo secret
- [ ] Trigger the workflow once manually, confirm rows land in Neon
- [ ] (Optional) Custom domain on Vercel + a `mcp.…` subdomain on Cloudflare
- [ ] Repoint Claude Desktop / Claude.ai to the deployed MCP URL

## Phase C — known follow-ups (don't block on these)

- [ ] Port `scout/` adapters into `platform/apps/scrapers/scrapers/adapters/` one venue at a time (the API now matches scout's exactly — most ports are: copy the file, swap `scout.x` → `..x` imports, add `@register`, add to `adapters/__init__.py::load_all()`)
- [ ] Add a "Refresh" button on the platform website that triggers a GitHub Actions `workflow_dispatch` (live `scout/` does this in-process; serverless deployment can't, so route it through Actions)
- [ ] Live venue map widget on `/venues/[slug]` — port Leaflet block from `scout/web/templates/theatre.html`, source coordinates from `theatre-coords.yaml`
- [ ] "New" filter chip on `/shows` should query `first_seen_at` directly (currently falls back to recent ordering)
- [ ] Replace the rule-based recommender in `apps/website/lib/recommend.ts` with an Anthropic call once the tag taxonomy is rich enough
- [ ] Flesh out the stubbed `/openapi.json` in `apps/mcp-server/src/index.ts` for the Custom GPT
- [ ] Email integration (Beehiiv or Buttondown) — pull "new this week" via the API on a cron
- [ ] Social bot (Buffer + Make.com) — post new listings, throttled
- [ ] Admin CMS — password-protected `/admin` for manual entry and corrections
- [ ] Pick a real name (placeholder is *Anywhere But The West End* — see [`platform/docs/POSITIONING.md`](platform/docs/POSITIONING.md))

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
