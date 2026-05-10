# System architecture

## Architectural principle

**One core, many surfaces.** Like a power station with multiple outlets — the database and Internal API are the generator; the website, email, MCP server, GPT, and social automation all draw from the same supply. Build the generator once. Add outlets as channels prove out.

## Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  AUDIENCES                                                    │
│  Web visitors · Subscribers · Claude · ChatGPT · Social      │
└─────▲──────────▲───────────▲──────────▲──────────▲──────────┘
      │          │           │          │          │
┌─────┴──────────┴───────────┴──────────┴──────────┴──────────┐
│  SURFACES                                                     │
│  Website   Email      MCP Server    Custom GPT    Social Bot │
│  (Next.js) (Beehiiv)  (TS+Workers)  (OpenAPI)     (Buffer)   │
└────────────────────────────▲─────────────────────────────────┘
                             │
                  ┌──────────┴──────────┐
                  │   INTERNAL API      │  ← single source of truth
                  │   (REST or GraphQL) │
                  └──────────▲──────────┘
                             │
                  ┌──────────┴──────────┐
                  │  DATABASE (Postgres)│
                  │  venues · shows ·   │
                  │  performances · tags│
                  └──────────▲──────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│  INGESTION                                                    │
│  Scrapers (per venue) · Partner feeds · Admin CMS            │
└────────────────────────────▲─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│  SOURCES                                                      │
│  70 theatre sites · Partner data · You (manual curation)     │
└──────────────────────────────────────────────────────────────┘
```

## The single most important rule

Every surface talks to the **Internal API**, never to the database directly. If a surface needs data, it asks the API. This is what lets you change the website without breaking the GPT, or swap the database without touching the MCP server.

---

## Layer-by-layer

### Sources & Ingestion

Three feeds, increasing in reliability: **scrapers** (for venues with structured listings pages), **partner feeds** (later, when theatres start sending data directly), and a simple **admin CMS** for manual entry and exceptions. All routes funnel through a normalisation step that enforces a consistent schema before anything hits the DB.

### Database

Postgres. Roughly four tables: `venues`, `shows`, `performances`, `tags`. Add **PostGIS** for location queries — *"near London Bridge / within walking distance"* becomes a one-liner. Postgres' built-in full-text search handles *"find shows about grief"* without a separate search service. Boring choice on purpose.

### Internal API

REST or GraphQL — your call. Either way, this is the *contract* that every surface depends on. Versioned URL (`/v1/...`) from day one.

### Surfaces

| Surface | Tech | Notes |
|---------|------|-------|
| Website | Next.js | Browsable listings, show pages, neighbourhood/genre landing pages for SEO |
| Email | Beehiiv or Buttondown | Pulls "new this week" via API on a cron, weekly digest |
| MCP server | TypeScript SDK + Cloudflare Workers | Wraps API endpoints as tools (`search_shows`, `whats_on`, etc.) |
| Custom GPT | OpenAI Actions + OpenAPI | Same backend as everything else; zero extra service |
| Social bot | Buffer + Make.com | Auto-post new listings, throttled and curated |

---

## One opinionated stack

- Next.js + TypeScript on Vercel (website + API routes)
- Postgres on Supabase or Neon (managed, cheap, PostGIS-ready)
- MCP server in TypeScript on Cloudflare Workers
- Beehiiv (email), Buffer + Make.com (social)
- Admin CMS: a password-protected Next.js admin page is enough to start

Everything except the MCP server can live in one Next.js monorepo initially. Extract the API into its own service only if/when needed.

---

## TDD touchpoints (where it pays off most)

- **Scrapers** — highest value. Each venue's scraper gets a saved HTML fixture and a test pinning expected output. Sites change layouts; tests catch breakage before users see stale data.
- **MCP tool contracts** — every tool's input/output schema gets tested. AIs are unforgiving of inconsistent return shapes.
- **Recommendation logic** — pure functions, easy to test, high payoff because this is the magic of the AI experience.
- **API endpoints** — standard contract tests. Less critical if the surfaces above are well-tested.

## Documentation layout

- `README.md` — architecture overview (this diagram), repo map, getting-started
- `apps/website/README.md` — frontend specifics
- `apps/scrapers/README.md` — how to add a new venue scraper, fixture conventions
- `apps/mcp-server/README.md` — deployment, env vars
- `docs/TOOL_SURFACE.md` — the spec for every MCP tool. **The most important doc.**
