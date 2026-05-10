# website

The Next.js app. Hosts three things at once:

1. **Public site** — listings pages at `/`, `/shows/[slug]`, `/venues/[slug]`, neighbourhood + genre landing pages for SEO.
2. **Admin CMS** — a password-protected `/admin` (later phase) for manual entry and corrections.
3. **Internal API** — the source of truth that every other surface consumes, mounted at `/api/v1`.

## Why one app?

Per `docs/ARCHITECTURE.md`:

> Everything except the MCP server can live in one Next.js monorepo initially. Extract the API into its own service only if/when needed.

Hosting the API as Next.js route handlers keeps the contract (`@platform/shared`) and the implementation in one place. The MCP server, custom GPT, and any future client all hit `/api/v1` over HTTP — they have no privileged path.

## Layout

```
app/
  page.tsx                    Home — current listings
  shows/[slug]/page.tsx       Show detail page (SSR'd from API)
  venues/[slug]/page.tsx      Venue page
  api/v1/
    shows/route.ts            GET search_shows
    shows/[id]/route.ts       GET get_show
    venues/route.ts           GET search_venues
    venues/[id]/route.ts      GET get_venue
    whats-on/route.ts         GET whats_on
    recommend/route.ts        POST recommend_shows
lib/
  db.ts                       postgres.js singleton
  queries/
    shows.ts                  search(), getById(), getBySlug()
    venues.ts                 search(), getById(), getBySlug()
  recommend.ts                vibe-string → ranked shows + reasons
  time.ts                     resolves whats_on `when` enum to a Europe/London window
```

## API routes

Every route validates input with the zod schema from `@platform/shared/schemas`, runs the matching query, and returns JSON shaped to `@platform/shared/types`. **No business logic in the MCP server** — all of it lives here so every surface gets the same answer.

```bash
# search_shows — flexible
curl 'http://localhost:3000/api/v1/shows?neighbourhood=Hackney&max_price=20'

# whats_on
curl 'http://localhost:3000/api/v1/whats-on?when=this_weekend&near=London%20Bridge'

# recommend
curl -X POST http://localhost:3000/api/v1/recommend \
  -H 'content-type: application/json' \
  -d '{"vibe": "weird and political", "constraints": {"max_price": 15}}'
```

## Dev

```bash
cp ../../.env.example .env.local
# fill DATABASE_URL
pnpm dev    # http://localhost:3000
```

If the DB has no data yet, the homepage shows an empty state. Apply schema and seed first (`packages/db/README.md`).
