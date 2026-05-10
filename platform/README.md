# Platform

Multi-surface listings platform for London's non-West End theatres.

**Architectural rule:** one core, many surfaces. The database and Internal API are the generator; the website, email, MCP server, custom GPT, and social automation all draw from the same supply. **Every surface talks to the Internal API, never to the database directly.**

```
┌─────────────────── AUDIENCES ────────────────────┐
│ Web · Email · Claude · ChatGPT · Social          │
└──────────────────────▲───────────────────────────┘
                       │
┌─────────────────── SURFACES ─────────────────────┐
│ apps/website   apps/mcp-server   (email, social) │
└──────────────────────▲───────────────────────────┘
                       │
              ┌────────┴─────────┐
              │  INTERNAL API     │   apps/website/app/api/v1
              └────────▲─────────┘
                       │
              ┌────────┴─────────┐
              │  POSTGRES + GIS   │   packages/db
              └────────▲─────────┘
                       │
┌─────────────────── INGESTION ────────────────────┐
│ apps/scrapers (one adapter per venue)            │
└──────────────────────▲───────────────────────────┘
                       │
              ┌────────┴─────────┐
              │  70 theatre sites │
              └──────────────────┘
```

## Repo layout

```
apps/
  website/        Next.js 15 — public site + admin CMS + Internal API (/api/v1)
  mcp-server/     TypeScript MCP server on Cloudflare Workers
  scrapers/       Python ingestion adapters

packages/
  db/             Postgres schema + migrations (PostGIS, full-text search)
  shared/         TypeScript types + zod schemas (the contract)

docs/
  ARCHITECTURE.md   System diagram, layer-by-layer, opinionated stack
  TOOL_SURFACE.md   MCP tool API spec — the most important doc
  BUILD_PLAN.md     Three-phase delivery plan
```

## Quick start

- **[SETUP.md](SETUP.md)** — local dev: prerequisites, Docker Postgres, env, Claude Desktop wiring.
- **[DEPLOY.md](DEPLOY.md)** — production: Vercel, Neon, Cloudflare Workers, GitHub Actions cron.

TL;DR:

```bash
pnpm install
docker run --name listings-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=listings -p 5432:5432 -d postgis/postgis:16-3.4
docker exec -i listings-pg psql -U postgres -d listings < packages/db/schema.sql
docker exec -i listings-pg psql -U postgres -d listings < scripts/seed.sql
cp .env.example .env
pnpm --filter website dev          # http://localhost:3000
```

## Conventions

- TypeScript everywhere except scrapers (Python — same parsing patterns we already know).
- Types live in `packages/shared` and are validated at every boundary with zod.
- Database access is centralised in the website app (`apps/website/lib/queries/`). The MCP server **never** opens a DB connection — it only calls the Internal API.
- API versioned at `/api/v1/...` from day one. Breaking changes bump to `/v2`.
- One adapter per venue, one fixture per adapter, one parse-test per adapter.

## Aligned with `scout/`

Everything below was lifted byte-for-byte (or near it) from the production `scout/` site at the repo root, so a future port of any scout adapter / UI piece is mechanical:

| Concern | Scout | Platform |
|---------|-------|----------|
| HTTP engine | `scrapling.fetchers.FetcherSession` + `StealthySession` | same — `apps/scrapers/scrapers/http.py` |
| Adapter API | `BaseAdapter` with `parse(html, base_url) → list[Show]` and `enrich(html, base_url) → dict` | same — `apps/scrapers/scrapers/adapters/base.py` |
| Generic adapter | `(slug, url, css)` tuples in `scout/adapters/bulk.py` | same — `apps/scrapers/scrapers/adapters/bulk.py` |
| Show classifier | `scout/classify.py` | ported verbatim — `apps/scrapers/scrapers/classify.py` |
| JSON-LD + date helpers | `scout/adapters/_jsonld.py`, `_html.py` | ported verbatim |
| Text helpers | `scout/text.py`, `scout/enrich.py` | ported verbatim |
| Orchestrator | 3-phase: serial listings → parallel enrich (round-robin) → serial DB writes | same — `apps/scrapers/scrapers/runner.py` |
| Show data shape | `theatre_slug`, `url`, `start_date`, `end_date`, `image_url`, `price_min/max` (pence) | same on the adapter side; the writer maps onto `venue_id`, `booking_url`, `price_min_pence` etc. |
| Design system | Swiss Index (`design-guide/theatre-scout.css`) + page chrome (`scout/web/static/style.css`) | imported by `apps/website/app/globals.css` |
| UI pages | Home venue index · `/shows` rails+list · `/theatres/<slug>` | mirror in Next.js — `app/page.tsx` · `app/shows/page.tsx` · `app/venues/[slug]/page.tsx` |
| Filter chips | Today / This week / New + type + venue tier + sort | same URL-encoded shape on `/shows` |
| Per-row split | Title links external (booking), venue links internal | same |

## What's intentionally NOT here yet

- Email sender (Beehiiv / Buttondown integration) — Phase 1 add-on.
- Social-bot automation (Buffer / Make.com).
- Custom GPT (OpenAPI export from `/api/v1` — generate at launch time).
- Auth — listings are public, so the read API is unauthenticated. Admin CMS gets a single password later.

See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).
