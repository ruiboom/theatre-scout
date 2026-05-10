# Setup

Step-by-step for everything you need to do outside Claude Code to get this platform running locally and (later) deployed.

Commands assume your shell is in this `platform/` directory unless otherwise noted.

---

## 0. One-time prerequisites

Skip any you already have.

```bash
# Node 20+ and pnpm (the JS workspace tool)
brew install node@20
corepack enable
corepack prepare pnpm@9.12.0 --activate

# Python 3.11+ and uv (you already use uv for scout/)
brew install python@3.12 uv

# Docker (easiest way to run Postgres + PostGIS)
brew install --cask docker
open -a Docker         # start Docker Desktop, leave it running

# (later, only when deploying the MCP server) Cloudflare account + wrangler login
# pnpm dlx wrangler login   # opens a browser; skip until you're ready to deploy
```

Sanity check:

```bash
node -v        # >= v20
pnpm -v        # 9.x
uv --version
docker version
```

---

## 1. Install JS dependencies

```bash
cd platform
pnpm install
```

Pulls everything for `apps/website`, `apps/mcp-server`, `packages/shared`, `packages/db`. First run takes ~1–2 min; subsequent ones are fast.

---

## 2. Boot Postgres + PostGIS locally

Using the official PostGIS image — Postgres 16 with PostGIS 3.4 already installed:

```bash
docker run --name listings-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=listings \
  -p 5432:5432 \
  -d postgis/postgis:16-3.4

# verify
docker ps   # should show listings-pg as "Up"
```

To stop/start later: `docker stop listings-pg` / `docker start listings-pg`. Data persists between restarts (deleting the container with `docker rm -f listings-pg` wipes it).

If you'd rather use Homebrew Postgres: `brew install postgresql@16 postgis && brew services start postgresql@16` and then `createdb listings && psql listings -c 'CREATE EXTENSION postgis;'`. Docker is less hassle.

---

## 3. Apply the schema and seed sample data

From `platform/`:

```bash
# schema (tables, indexes, FTS, GIST)
docker exec -i listings-pg psql -U postgres -d listings < packages/db/schema.sql

# 3 venues, 6 shows, performances across today/week/month
docker exec -i listings-pg psql -U postgres -d listings < scripts/seed.sql

# spot check
docker exec -i listings-pg psql -U postgres -d listings -c "SELECT slug, title FROM shows;"
```

You should see 6 show rows printed.

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Open `platform/.env` and confirm:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/listings
API_BASE_URL=http://localhost:3000/api/v1
MCP_API_BASE_URL=http://localhost:3000/api/v1
```

The defaults match the Docker setup above. The `ANTHROPIC_API_KEY` line can stay empty — the recommender falls back to rule-based ranking when it's unset.

Next.js looks for `.env.local` inside the website app, but `transpilePackages` + a workspace-root `.env` works in dev. If a route says `DATABASE_URL is not set`, also drop a copy in `apps/website/.env.local`.

---

## 5. Run the website + Internal API

```bash
pnpm --filter website dev
```

Open <http://localhost:3000> — you should see the homepage with the 6 seeded shows.

---

## 6. Verify each API endpoint

In a second terminal:

```bash
# search_shows — defaults to this week
curl -s 'http://localhost:3000/api/v1/shows' | jq '.total, .shows[0].title'

# whats_on this weekend
curl -s 'http://localhost:3000/api/v1/whats-on?when=this_weekend' | jq '.window, .total'

# recommend by vibe
curl -s -X POST http://localhost:3000/api/v1/recommend \
  -H 'content-type: application/json' \
  -d '{"vibe":"weird and political","constraints":{"max_price":20}}' | jq '.recommendations[].show.title'

# get_show by slug
curl -s 'http://localhost:3000/api/v1/shows/the-borrowed-time' | jq '.title, .creators'

# search_venues
curl -s 'http://localhost:3000/api/v1/venues?neighbourhood=Finsbury%20Park' | jq

# get_venue + current shows
curl -s 'http://localhost:3000/api/v1/venues/bush-theatre' | jq '.name, .current_shows | length'
```

If any of these throw, that's the layer to debug first — every other surface flows through these endpoints.

---

## 7. Set up the Python scrapers

In a third terminal:

```bash
cd platform/apps/scrapers
uv sync                  # creates .venv, installs deps from pyproject.toml

# the .env at platform/.env is read; or copy it here:
cp ../../.env .env

uv run scrape list       # registered adapters (just `example` for now)
uv run scrape venue example   # writes the placeholder show into the DB
```

Re-running `curl http://localhost:3000/api/v1/shows` should now show 7 shows — the scaffold's example show plus the 6 seeded ones, proving the writer is wired correctly.

(You'll need an `example` venue row first if you want the example adapter to actually write — easiest path is to drop one into `seed.sql` or add it via the scraper writer flow when porting real adapters.)

---

## 8. Run the MCP server locally

In a fourth terminal:

```bash
pnpm --filter mcp-server dev
```

Wrangler boots the worker on <http://localhost:8787>. The MCP endpoint is at `/mcp`.

```bash
curl http://localhost:8787/health    # {"ok":true}
```

The first run will prompt you to log into Cloudflare *only if you try to deploy* — `wrangler dev` runs locally without an account.

---

## 9. Connect Claude Desktop to your local MCP server

Edit (create if missing):

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "anywhere-but-west-end": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8787/mcp"]
    }
  }
}
```

Quit and re-open Claude Desktop (⌘Q first; closing the window isn't enough). In a new chat you should see the six tools available. Try:

> *what's on this weekend in Finsbury Park under £20?*

Claude should call `whats_on` and reply with the seeded shows.

If your Claude Desktop is recent enough to support direct URL config, you can also use:

```json
{ "mcpServers": { "anywhere-but-west-end": { "url": "http://localhost:8787/mcp" } } }
```

---

## 10. Run the test suite

```bash
# JS tests across the workspace (shared, website, mcp-server)
pnpm test

# Python tests
cd apps/scrapers && uv run pytest
```

---

## 11. (Later — when you're ready to ship)

**Website** → Vercel:

```bash
cd platform/apps/website
pnpm dlx vercel link
pnpm dlx vercel env add DATABASE_URL    # paste your hosted DB URL (Supabase/Neon)
pnpm dlx vercel deploy --prod
```

Hosted Postgres options: [Supabase](https://supabase.com/) or [Neon](https://neon.tech/) — both free tiers, both ship PostGIS.

**MCP server** → Cloudflare Workers:

```bash
cd platform/apps/mcp-server
pnpm dlx wrangler login
pnpm dlx wrangler secret put API_BASE_URL    # https://your-vercel-domain.com/api/v1
pnpm deploy
```

Public URL becomes `https://platform-mcp-server.<account>.workers.dev/mcp` — submit that to Claude's app directory when you're ready for the AI launch.

**Custom GPT** → make `/openapi.json` real (it's currently stubbed in `apps/mcp-server/src/index.ts`), then point an OpenAI Custom GPT Action at it. Same backend, second storefront.

---

## Daily dev loop after first setup

```bash
docker start listings-pg
cd platform
pnpm --filter website dev          # terminal 1
pnpm --filter mcp-server dev       # terminal 2 (only if working on MCP)
```

Stop everything with `Ctrl-C` in each terminal and `docker stop listings-pg`.
