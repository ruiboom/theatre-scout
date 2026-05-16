# Platform — Technical Documentation

**Anywhere But West End** — multi-surface listings platform for London's ~70 non-West End theatres.

Production: <https://theatre-scout-zunz.vercel.app>

This README is the complete technical reference for the deployed online platform. For the local Python research app at the repo root (`scout/`), see the root `README.md` and `CLAUDE.md` — that codebase is independent.

For other audiences:

- **Visitors / admins** → [USER_GUIDE.md](USER_GUIDE.md).
- **Ops / domains / billing** → [MANAGEMENT_PLAYBOOK.md](MANAGEMENT_PLAYBOOK.md).
- **First-time local setup** → [SETUP.md](SETUP.md).
- **First-time deploy** → [DEPLOY.md](DEPLOY.md).
- **MCP tool surface** → [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md).

---

## 1. What this is

A daily-scraped database of London non-West End theatre productions, exposed through three surfaces:

| Surface | Audience | Hosted on |
|---------|----------|-----------|
| Next.js website + admin CMS | Humans | Vercel |
| MCP server (six tools) | Claude / agents | Cloudflare Workers |
| OpenAPI export (`/api/openapi`) | Custom GPT, third-party clients | Vercel (same Next.js app) |

All three read from the same Postgres database via the same Internal API. Ingestion is a separate Python pipeline that runs on GitHub Actions, on a daily cron and on demand.

### Architectural rule

**One core, many surfaces.** The database and Internal API are the single source of truth. The website, MCP server, future email sender, future social bot — every surface goes through `/api/v1/*`. **No surface opens a DB connection except the website.**

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
              │  POSTGRES + GIS   │   packages/db  (hosted on Neon)
              └────────▲─────────┘
                       │
┌─────────────────── INGESTION ────────────────────┐
│ apps/scrapers (one adapter per venue, ~70)       │
└──────────────────────▲───────────────────────────┘
                       │
              ┌────────┴─────────┐
              │  70 theatre sites │
              └──────────────────┘
```

---

## 2. Repo layout

```
platform/
├── apps/
│   ├── website/        Next.js 15 — public site + admin CMS + Internal API (/api/v1)
│   ├── mcp-server/     TypeScript MCP server on Cloudflare Workers
│   └── scrapers/       Python ingestion adapters
│
├── packages/
│   ├── db/             Postgres schema + migrations (PostGIS, FTS, pg_trgm)
│   └── shared/         TypeScript types + zod schemas — the cross-app contract
│
├── docs/
│   ├── ARCHITECTURE.md       System diagram, layer-by-layer
│   ├── TOOL_SURFACE.md       MCP tool API spec
│   ├── POSITIONING.md        Product positioning
│   ├── AUDIENCE.md           Target users
│   └── BUILD_PLAN.md         Three-phase delivery plan
│
├── scripts/
│   ├── etl_from_scout.py     One-shot import from scout/ SQLite DB
│   └── seed.sql              Local dev seed data
│
├── README.md           ← you are here (technical reference)
├── USER_GUIDE.md       End user + admin guide
├── MANAGEMENT_PLAYBOOK.md  Ops: Vercel/Neon/Cloudflare
├── SETUP.md            Local dev quick-start
├── DEPLOY.md           First-time prod deployment
├── pnpm-workspace.yaml
├── turbo.json
├── tsconfig.base.json
└── .env.example
```

---

## 3. Stack

| Layer | Choice |
|-------|--------|
| Website | Next.js 15 (App Router), React 19, TypeScript |
| Database | Neon Postgres 16 (serverless) with PostGIS, pg_trgm |
| DB driver (website) | `postgres` (template-literal queries, no ORM) |
| DB driver (scrapers) | `psycopg[binary]` 3.x |
| Maps | Leaflet (client-side) |
| Validation | zod (TS), pydantic v2 (Python) |
| MCP server | Cloudflare Workers, Hono, `@modelcontextprotocol/sdk`, `agents` framework |
| MCP session storage | Durable Object (`ListingsMCP`) backed by Workers SQLite |
| Scrapers (HTTP) | Scrapling: `FetcherSession` (curl_cffi) fast path, `StealthySession` (Patchright/Chromium) for anti-bot/JS-rendered sites |
| Scrapers (parse) | `scrapling.parser.Selector` (BS4-style API) |
| Scrapers (CLI) | Typer |
| Package manager | pnpm (workspaces) — JS; uv — Python |
| Build pipeline | Turbo |
| Source control + CI / cron | GitHub (`ruiboom/theatre-scout`, **public**); GitHub Actions for the daily scrape |

Reasoning for each choice lives in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 4. Application: `apps/website` (Next.js)

Hosts everything humans see and most of what machines see. Single Next.js project, App Router, all pages `force-dynamic` to guarantee fresh DB reads (no ISR — the data shape is small enough that querying directly per request is fine and Neon's pooled connection makes it cheap).

### 4.1 Routes

#### Public pages (SSR)

| Path | Purpose |
|------|---------|
| `GET /` | Home — venue index + hero stats |
| `GET /shows` | Show index — filters (time window, type, tier, sort), rails + list, search |
| `GET /shows/[slug]` | Show detail — performances, creators, content warnings, book tickets |
| `GET /venues/[slug]` | Venue detail — Leaflet map, current shows, box office link |
| `GET /about` | Static |

#### Admin pages (cookie-gated by `isAdmin()`)

| Path | Purpose |
|------|---------|
| `GET /admin/login` | Password form. Server action `attemptLogin(formData)` does timing-safe compare against SHA-256 of `ADMIN_PASSWORD`. |
| `GET /admin` | Dashboard — visit totals, top searches, top venue clicks, top outbound clicks, last scrape status. Button calls server action `triggerRefresh()`. |

Session = signed cookie `ts_admin` (HTTP-only, 14-day max-age, Lax SameSite, Secure in production).

#### Internal API (`/api/v1/*`, public, no auth)

Every endpoint validates input with the zod schemas from `@platform/shared`.

| Method + path | Backs MCP tool | Notes |
|---------------|----------------|-------|
| `GET /api/v1/shows` | `search_shows` | Params: `date_from`, `date_to`, `neighbourhood`, `near={lat,lng,radius_km}`, `max_price`, `min_price`, `genres[]`, `tags[]`, `venue_ids[]`, `limit` (1–50). Defaults today→+7d, sort `start_date ASC`. |
| `GET /api/v1/shows/{id_or_slug}` | `get_show` | UUID → ID lookup; else slug. Returns `ShowDetail` (full description, performances, reviews, creators). |
| `GET /api/v1/venues` | `search_venues` | Fuzzy name (pg_trgm), neighbourhood, geo, limit. |
| `GET /api/v1/venues/{id_or_slug}?include_shows=true` | `get_venue` | Optional `current_shows[]`. |
| `GET /api/v1/whats-on` | `whats_on` | `when=tonight\|tomorrow\|this_weekend\|next_weekend\|this_week`, optional `near` (string or `{lat,lng}`), `max_price`. Time windows resolved in `Europe/London`. |
| `POST /api/v1/recommend` | `recommend_shows` | Body `{ vibe, constraints?, exclude_genres?, limit? }`. Currently token-overlap; LLM-backed once `ANTHROPIC_API_KEY` wired. |
| `POST /api/v1/events` | — | Client-side analytics `{ type, path?, target?, query? }`. |
| `POST /api/v1/admin/refresh` | — | Admin-only. Dispatches `scrape.yml` via GitHub REST API. |
| `GET /api/openapi` | — | OpenAPI 3.0 export consumed by the Custom GPT. |
| `GET /r?type=outbound&target=<slug>&to=<url>` | — | Tracked redirect. Records outbound event, validates `to` is `http(s)://`, 302s. |

### 4.2 Code map

```
apps/website/
├── app/
│   ├── (public pages — page.tsx files per route)
│   ├── admin/
│   │   ├── login/page.tsx
│   │   └── page.tsx
│   ├── api/
│   │   ├── v1/...           Internal API endpoints
│   │   └── openapi/route.ts OpenAPI 3.0 export
│   └── r/route.ts           Tracked redirect
├── components/              React components (cards, filters, map)
├── lib/
│   ├── auth.ts              isAdmin(), attemptLogin(), cookie helpers
│   ├── db.ts                postgres client (uses DATABASE_URL)
│   ├── github.ts            triggerRefresh() — dispatches Actions workflow
│   └── queries/
│       ├── shows.ts         searchShows(), getShow()
│       ├── venues.ts        searchVenues(), listVenuesWithCounts(), getVenue()
│       └── events.ts        visitTotals(), topSearches(), topVenueClicks(),
│                            topShowClicks(), scrapeStatus()
├── next.config.ts
└── package.json
```

All DB access is centralised in `lib/queries/`. Components never call the DB directly. The MCP server never calls the DB at all — it talks HTTP to `/api/v1/*`.

### 4.3 Environment variables

| Name | Required | Purpose |
|------|----------|---------|
| `DATABASE_URL` | **yes** | Neon pooled connection string (ends in `-pooler.neon.tech`) |
| `NEXT_PUBLIC_SITE_URL` | no | Canonical URL (defaults to the Vercel domain). Used in OpenAPI export and metadata. |
| `ADMIN_PASSWORD` | no | Single password for `/admin`. If unset, all admin routes 500 (safe default). |
| `GITHUB_TOKEN` | no | Fine-grained PAT with `Actions: read & write` on `ruiboom/theatre-scout`. Required to use the Refresh button. |
| `GITHUB_REPO` | no | Defaults `ruiboom/theatre-scout`. |
| `GITHUB_WORKFLOW` | no | Defaults `scrape.yml`. |
| `ANTHROPIC_API_KEY` | no | For future LLM-backed `recommend_shows`. |

See [.env.example](.env.example).

---

## 5. Application: `apps/mcp-server` (Cloudflare Worker)

Thin HTTP wrapper that exposes six tools to MCP clients (Claude Desktop, Anthropic API, custom agents). No database access, no business logic — each tool is one fetch to `/api/v1/*`.

### 5.1 Endpoints

| Path | Purpose |
|------|---------|
| `GET /mcp` | MCP transport (SSE/streamable HTTP). The URL clients register. |
| `GET /openapi.json` | OpenAPI 3.0 export (mirrors `/api/openapi` on the website). |
| `GET /health` | Returns `{ ok: true }` |

### 5.2 Tools

| Tool | Backs which endpoint |
|------|----------------------|
| `search_shows` | `GET /api/v1/shows` |
| `get_show` | `GET /api/v1/shows/{id_or_slug}` |
| `whats_on` | `GET /api/v1/whats-on` |
| `recommend_shows` | `POST /api/v1/recommend` |
| `search_venues` | `GET /api/v1/venues` |
| `get_venue` | `GET /api/v1/venues/{id_or_slug}` |

Tool schemas come from `@platform/shared/schemas` — same zod source as the API.

The contract and design principles ("few tools, consistent shapes, sensible defaults, fail loudly") are in [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md).

### 5.3 Configuration

`wrangler.toml` (excerpt):

```toml
name = "platform-mcp-server"
main = "src/index.ts"
compatibility_date = "2025-01-01"
compatibility_flags = ["nodejs_compat"]

[durable_objects]
bindings = [
  { name = "MCP_OBJECT", class_name = "ListingsMCP" }
]

[[migrations]]
tag = "v1"
new_sqlite_classes = ["ListingsMCP"]

[vars]
API_BASE_URL = "https://theatre-scout-zunz.vercel.app/api/v1"
```

Set `API_BASE_URL` as a secret (overrides the var) when pointing at a non-default backend:

```bash
wrangler secret put API_BASE_URL
```

### 5.4 Deployed URL

```
https://platform-mcp-server.<cloudflare-account>.workers.dev/mcp
```

Account-scoped subdomain. The MCP playbook covers attaching a custom domain.

---

## 6. Application: `apps/scrapers` (Python)

Daily ingestion. ~70 adapters (one per venue), three-phase orchestrator, writes directly to Postgres.

### 6.1 Layout

```
apps/scrapers/
├── pyproject.toml
└── scrapers/
    ├── cli.py              Typer CLI: list | venue | all | sync-venues
    ├── runner.py           Three-phase orchestrator; records ScrapeRun
    ├── writer.py           psycopg bulk upsert; Show → DB column mapping
    ├── models.py           Show, Theatre, ScrapeRun (pydantic, scout-compatible)
    ├── http.py             Scrapling client + per-host rate limit (1 req/s)
    ├── text.py / enrich.py Text + image extraction helpers
    ├── classify.py         Show-type heuristic classifier (play/musical/...)
    └── adapters/
        ├── base.py         BaseAdapter abstract class
        ├── _jsonld.py      schema.org Event/TheaterEvent extractor
        ├── _html.py        British date-range parser
        ├── bulk.py         GenericAdapter tuples (slug, url, css) — the long tail
        ├── example.py      Template for bespoke adapters
        └── <slug>.py       Bespoke adapters (one per venue when generic fails)
```

### 6.2 Adapter contract

```python
class BaseAdapter:
    slug: str
    url: str
    requires_js: bool = False         # True → use Patchright headless instead of curl_cffi

    def parse(self, html: str, base_url: str) -> list[Show]:
        ...

    def enrich(self, html: str, base_url: str) -> dict:
        """Optional. Detail-page scrape, merged onto the parsed Show."""
        return {}
```

`Show` shape (adapter-facing — see `models.py`):

```python
class Show:
    theatre_slug: str
    title: str
    url: str
    start_date: date | None
    end_date: date | None
    price_min: int | None           # pence
    price_max: int | None           # pence
    image_url: str | None
    description_short: str | None
    description_full: str | None
    show_type: str                  # play | musical | comedy | dance | opera | family | cabaret | other
    writer: str | None
    director: str | None
    cast_members: list[str]
    content_warnings: list[str]
    reviews_summary: str | None
    raw_data: dict                  # JSON-LD blob or scrape artefact
```

The writer (`writer.py`) translates this to the DB schema (`theatre_slug` → `venue_id`, `price_min` → `price_min_pence`, `url` → `booking_url`, generates `slug`).

### 6.3 Three-phase orchestrator

1. **Parse** (serial) — each adapter's `parse()` on the listings page; staged in memory.
2. **Enrich** (parallel, round-robin) — fetch each show's detail page, call `enrich()`. Round-robins workers across distinct hosts to stay polite per host.
3. **Write** (serial) — bulk upsert on `(venue_id, title, start_date)`. With `--replace`, prunes shows from that venue not seen this run. Records one `scrape_runs` row per venue (status: `success | partial | failed`).

Failure isolation: one adapter raising does not crash the run. The failing venue gets a `failed` ScrapeRun with the exception message.

### 6.4 CLI

```bash
uv run scrape list                                            # registered venues
uv run scrape venue almeida                                   # one venue, parse only
uv run scrape venue almeida --enrich --replace --workers 4    # one venue, full pipeline
uv run scrape all --enrich --replace --workers 16             # everything
uv run scrape sync-venues ../../../theatres.yaml              # idempotent venue metadata sync
```

### 6.5 Environment

| Name | Purpose |
|------|---------|
| `DATABASE_URL` | Neon **direct** (non-pooled) URL — pooler is for short-lived serverless connections; the scraper holds a long connection and bulk-inserts. |

### 6.6 Scheduling — GitHub Actions

Workflow: `.github/workflows/scrape.yml` (at repo root, named **"Daily scrape"**). Triggers:

- `schedule: cron: "0 5 * * *"` — every day at 05:00 UTC.
- `workflow_dispatch` — manual (Actions tab, and the admin Refresh button via REST API).

`concurrency: group: scrape, cancel-in-progress: false` — overlapping runs queue.

Job steps (ubuntu-latest, 45 min timeout, working dir `platform/apps/scrapers`):

1. Checkout
2. `astral-sh/setup-uv@v4` with `uv.lock` caching
3. Cache Patchright (Chromium) at `~/.cache/ms-playwright`
4. `uv sync`
5. `uv run scrapling install`
6. `uv run scrape sync-venues ../../../theatres.yaml`
7. `uv run scrape all --enrich --replace --workers 16`
8. Smoke test (only if `vars.SITE_BASE_URL` is set): `curl $SITE_BASE_URL/api/v1/shows?limit=1` and assert `total > 100`

Typical run: ~17 minutes. Data is current by 05:20 UTC.

GitHub Actions configuration (Repo → Settings → Secrets and variables → Actions):

| Kind | Name | Value |
|------|------|-------|
| Secret | `NEON_DATABASE_URL` | Neon **direct** URL with `?sslmode=require` |
| Variable | `SITE_BASE_URL` | `https://theatre-scout-zunz.vercel.app` |

Detailed ops for the workflow (rotation, manual triggers, failure modes) live in [MANAGEMENT_PLAYBOOK.md §4](MANAGEMENT_PLAYBOOK.md).

---

## 7. Package: `packages/db`

Canonical schema in `schema.sql`. Numbered migrations in `migrations/`.

### 7.1 Tables

#### `venues`

```sql
venues (
  id              UUID PRIMARY KEY,
  slug            TEXT UNIQUE,
  name            TEXT NOT NULL,
  neighbourhood   TEXT NOT NULL,
  postcode_prefix TEXT,
  nearest_tube    TEXT,
  description     TEXT DEFAULT '',
  capacity        INTEGER,
  address         TEXT DEFAULT '',
  location        GEOGRAPHY(POINT, 4326),
  website         TEXT DEFAULT '',
  category        TEXT CHECK (category IN ('major','mid','fringe','outer')),
  raw_data        JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)
-- Indexes: neighbourhood (B-tree), location (GIST), name (GIN trigram)
```

#### `shows`

```sql
shows (
  id                  UUID PRIMARY KEY,
  slug                TEXT UNIQUE,
  venue_id            UUID REFERENCES venues(id) ON DELETE CASCADE,
  title               TEXT NOT NULL,
  show_type           TEXT DEFAULT 'other'
                      CHECK (show_type IN ('play','musical','comedy','dance','opera','family','cabaret','other')),
  description_short   TEXT DEFAULT '',
  description_full    TEXT DEFAULT '',
  price_min_pence     INTEGER,
  price_max_pence     INTEGER,
  start_date          DATE,
  end_date            DATE,
  duration_minutes    INTEGER,
  age_rating          TEXT,
  content_warnings    TEXT[] DEFAULT '{}',
  image_url           TEXT,
  booking_url         TEXT DEFAULT '',
  writer              TEXT,
  director            TEXT,
  cast_members        TEXT[] DEFAULT '{}',
  reviews_summary     TEXT,
  search_tsv          TSVECTOR GENERATED ALWAYS AS (...) STORED,
  raw_data            JSONB DEFAULT '{}',
  first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (venue_id, title, start_date)
)
-- Indexes: venue_id, search_tsv (GIN FTS), title (GIN trigram),
--          start_date, end_date, first_seen_at DESC
```

#### `performances`

```sql
performances (
  id                          UUID PRIMARY KEY,
  show_id                     UUID REFERENCES shows(id) ON DELETE CASCADE,
  starts_at                   TIMESTAMPTZ NOT NULL,
  available_tickets_estimate  INTEGER,
  sold_out                    BOOLEAN DEFAULT FALSE,
  raw_data                    JSONB DEFAULT '{}',
  created_at                  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (show_id, starts_at)
)
-- Indexes: show_id, starts_at
```

#### `tags`, `show_tags`

Genre and free-form tags, joined many-to-many to shows.

#### `scrape_runs`

```sql
scrape_runs (
  id           UUID PRIMARY KEY,
  venue_slug   TEXT NOT NULL,
  started_at   TIMESTAMPTZ NOT NULL,
  finished_at  TIMESTAMPTZ,
  status       TEXT CHECK (status IN ('success','partial','failed','running')),
  shows_found  INTEGER DEFAULT 0,
  error        TEXT
)
-- Indexes: venue_slug, started_at DESC
```

#### `events`

```sql
events (
  id           UUID PRIMARY KEY,
  type         TEXT CHECK (type IN ('visit','search','outbound')),
  path         TEXT,
  target       TEXT,
  query        TEXT,
  occurred_at  TIMESTAMPTZ DEFAULT NOW()
)
```

No PII, no IP/UA columns by design.

### 7.2 Applying the schema

Fresh database:

```bash
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'
psql "$DATABASE_URL" -f packages/db/schema.sql
```

Migrations (rarely; applied in numeric order):

```bash
psql "$DATABASE_URL" -f packages/db/migrations/0001_init.sql
psql "$DATABASE_URL" -f packages/db/migrations/0002_align_with_scout.sql
psql "$DATABASE_URL" -f packages/db/migrations/0003_events.sql
```

There is no migration runner — they're applied by hand and committed to git. Acceptable at this scale; revisit if it stops being so.

---

## 8. Package: `packages/shared`

The cross-app type contract.

```
packages/shared/
├── types.ts       Show, ShowDetail, VenueSummary, VenueDetail, Recommendation
├── schemas.ts     zod: SearchShowsInput, SearchVenuesInput, WhatsOnInput,
│                       RecommendShowsInput, plus response schemas
└── index.ts
```

Imported by both the website (`apps/website`) and the MCP server (`apps/mcp-server`). They cannot drift — one zod schema, both ends validate against it.

```ts
import type { Show, ShowDetail } from '@platform/shared';
import { SearchShowsInput } from '@platform/shared';

const params = SearchShowsInput.parse(Object.fromEntries(req.nextUrl.searchParams));
```

---

## 9. Cross-cutting design decisions

| Concern | Decision | Why |
|---------|----------|-----|
| Normalisation | 1 show ⟂ many performances | "What's on tonight" stays a clean query |
| Price storage | pence in DB, GBP integers in API | no float, exact match to source data |
| Show identity | upsert on `(venue_id, title, start_date)` | same title, same venue, later season = new row |
| Slugs | slugified title + random suffix when collision | survives same-title revivals — see commit `9a4f301` |
| Auth | single password, SHA-256 cookie | no user management; admin is one person |
| MCP isolation | wrapper-only, no DB access | API is source of truth; website + MCP can never diverge |
| API versioning | `/api/v1/*` from day one | breaking changes go to `/v2` |
| Caching | none on `/api/v1` — everything `force-dynamic` | small data, fresh always; revisit if Neon costs spike |
| Search | Postgres FTS (tsvector, GIN) + pg_trgm | no separate search service; fuzzy venue lookup works |
| Geo | PostGIS `GEOGRAPHY(POINT, 4326)` + `ST_DWithin` | one-line "within X km of London Bridge" |
| Scraper concurrency | serial parse, parallel-by-host enrich, serial write | polite to source sites; resilient to per-venue failure |
| Headless browser | Patchright (Chromium) only when `requires_js = True` | most venues parse fine on curl_cffi |
| Failure mode | adapter raises → that venue's run goes `failed`, others continue | bad day for one venue ≠ outage for whole site |

---

## 10. Quick start (local dev)

Full instructions in [SETUP.md](SETUP.md). TL;DR:

```bash
pnpm install

docker run --name listings-pg \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=listings \
  -p 5432:5432 -d postgis/postgis:16-3.4

docker exec -i listings-pg psql -U postgres -d listings < packages/db/schema.sql
docker exec -i listings-pg psql -U postgres -d listings < scripts/seed.sql

cp .env.example .env

pnpm --filter website dev      # → http://localhost:3000
```

For the scrapers:

```bash
cd apps/scrapers
uv sync
uv run scrapling install         # Chromium for headless adapters
uv run scrape sync-venues ../../../theatres.yaml
uv run scrape venue almeida --enrich
```

For the MCP server locally:

```bash
cd apps/mcp-server
pnpm dev                          # wrangler dev → http://localhost:8787
```

---

## 11. Conventions

- **TypeScript everywhere** except the scrapers (Python — the parsing patterns already exist in `scout/` at the repo root).
- **Types in `packages/shared`**, validated at every boundary with zod.
- **DB access centralised** in `apps/website/lib/queries/`. The MCP server, scripts, and future surfaces go through the API.
- **API versioned at `/api/v1/`** from day one.
- **One adapter per venue, one fixture per adapter, one parse-test per adapter.**
- **`ruff format` + `ruff check`** clean for Python; standard ESLint/Prettier (Next defaults) for TS.
- **Small commits**; one adapter per commit when adding multiple.
- **Comments explain *why*, not *what*.**
- **No `TODO` without an owner.**

---

## 12. Aligned with `scout/` (root)

The platform's Python scrapers were lifted byte-for-byte from the local `scout/` research app, so porting any new adapter from scout is mechanical:

| Concern | Scout (root) | Platform |
|---------|--------------|----------|
| HTTP engine | `scrapling.fetchers.FetcherSession` + `StealthySession` | same — `apps/scrapers/scrapers/http.py` |
| Adapter API | `BaseAdapter` with `parse(html, base_url) → list[Show]` and `enrich(html, base_url) → dict` | same — `apps/scrapers/scrapers/adapters/base.py` |
| Generic adapter | `(slug, url, css)` tuples in `scout/adapters/bulk.py` | same — `apps/scrapers/scrapers/adapters/bulk.py` |
| Show classifier | `scout/classify.py` | ported verbatim |
| JSON-LD + date helpers | `scout/adapters/_jsonld.py`, `_html.py` | ported verbatim |
| Orchestrator | 3-phase: serial listings → parallel enrich → serial DB writes | same — `apps/scrapers/scrapers/runner.py` |
| Show data shape | `theatre_slug`, `url`, `start_date`, `end_date`, `image_url`, `price_min/max` (pence) | same on the adapter side; writer maps to DB columns |
| Design system | Swiss Index (`design-guide/theatre-scout.css`) + page chrome | imported by `apps/website/app/globals.css` |
| Filter chips | Today / This week / New + type + venue tier + sort | same URL-encoded shape on `/shows` |

`scout/` remains independent — it's the local research app with its own SQLite DB. The one-shot ETL script `platform/scripts/etl_from_scout.py` exists to seed the platform DB from scout's SQLite if needed.

---

## 13. What's intentionally not here yet

- **Email sender** (Beehiiv / Buttondown) — Phase 1.
- **Social bot automation** (Buffer / Make.com) — Phase 1.
- **Custom GPT** — built from `/api/openapi`; configure at openai.com.
- **LLM recommender** — `recommend_shows` is currently token-overlap. Wire `ANTHROPIC_API_KEY` and swap when ready.
- **Calendar view on `/shows`** — see memory note; rails + list shipped first.
- **Real auth** — listings are public; admin gets one password.

See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

---

## 14. Reference

- Architecture deep-dive — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- MCP tool spec — [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md)
- Positioning — [docs/POSITIONING.md](docs/POSITIONING.md)
- Audience — [docs/AUDIENCE.md](docs/AUDIENCE.md)
- Build plan — [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- Local setup — [SETUP.md](SETUP.md)
- Production deploy — [DEPLOY.md](DEPLOY.md)
- Ops playbook — [MANAGEMENT_PLAYBOOK.md](MANAGEMENT_PLAYBOOK.md)
- End-user / admin guide — [USER_GUIDE.md](USER_GUIDE.md)
