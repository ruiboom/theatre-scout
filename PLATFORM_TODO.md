# Platform — high-level TODO

Picking up the multi-surface platform later. The bootstrap lives in [`platform/`](platform/) — full architecture, six MCP tools, schema, scrapers, seed data — but nothing has been run yet.

This is the milestone-level view. Step-by-step commands are in [`platform/SETUP.md`](platform/SETUP.md) (local) and [`platform/DEPLOY.md`](platform/DEPLOY.md) (online).

> **Where this fits.** Per [`platform/docs/BUILD_PLAN.md`](platform/docs/BUILD_PLAN.md): the current `scout/` site is Phase 1 (ship the website, soft-launch ~1 Sept 2026). The `platform/` work is Phase 2 (Sept–Oct 2026: port to multi-surface, build the MCP server) and Phase 3 (Oct/Nov: AI-native launch moment).

---

## Phase A — run the platform locally

- [ ] Install prerequisites: Node 20, pnpm, uv, Docker Desktop
- [ ] `pnpm install` in `platform/`
- [ ] Boot Postgres + PostGIS via Docker (`postgis/postgis:16-3.4`)
- [ ] Apply `packages/db/schema.sql` and `scripts/seed.sql` to the local DB
- [ ] `cp .env.example .env`
- [ ] `pnpm --filter website dev` → homepage renders 6 seeded shows on :3000
- [ ] Smoke-test all six API endpoints (`/api/v1/shows`, `/whats-on`, `/recommend`, etc.)
- [ ] Wire up Python scrapers (`uv sync`, run `scrape venue example`) — verify the writer reaches Postgres
- [ ] `pnpm --filter mcp-server dev` → `:8787/health` returns ok
- [ ] Connect Claude Desktop via `mcp-remote`, confirm the six tools are callable
- [ ] `pnpm test` and `uv run pytest` both green

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

- [ ] Port `scout/` adapters into `platform/apps/scrapers/scrapers/adapters/` one venue at a time (see existing scout adapters as the reference)
- [ ] Replace the rule-based recommender in `apps/website/lib/recommend.ts` with an Anthropic call once the tag taxonomy is rich enough
- [ ] Flesh out the stubbed `/openapi.json` in `apps/mcp-server/src/index.ts` for the Custom GPT
- [ ] Email integration (Beehiiv or Buttondown) — pull "new this week" via the API on a cron
- [ ] Social bot (Buffer + Make.com) — post new listings, throttled
- [ ] Admin CMS — password-protected `/admin` for manual entry and corrections
- [ ] Pick a real name (placeholder is *Anywhere But The West End* — see [`platform/docs/POSITIONING.md`](platform/docs/POSITIONING.md))

---

## What's already done in the bootstrap

For reference when you come back — these are the artefacts in [`platform/`](platform/):

- Monorepo: pnpm workspaces + turbo
- `packages/shared` — types + zod schemas (the contract between every surface)
- `packages/db` — Postgres schema with PostGIS + tsvector FTS, migration runner
- `apps/website` — Next.js 15 App Router, six API routes with real SQL queries, server-rendered pages
- `apps/mcp-server` — TS MCP on Cloudflare Workers, six tools wired to the API via `agents/mcp`
- `apps/scrapers` — Python scaffolding (BaseAdapter, normalize, writer, CLI, example adapter)
- `scripts/seed.sql` — 3 venues, 6 shows, performances spanning today→next month
- `docs/` — copies of architecture, tool surface, build plan, positioning, audience strategy
