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

## What's intentionally NOT here yet

- Email sender (Beehiiv / Buttondown integration) — Phase 1 add-on.
- Social-bot automation (Buffer / Make.com).
- Custom GPT (OpenAPI export from `/api/v1` — generate at launch time).
- Auth — listings are public, so the read API is unauthenticated. Admin CMS gets a single password later.

See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).
