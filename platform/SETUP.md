# Setup

Step-by-step for everything you need to do outside Claude Code to get this platform running locally and (later) deployed.

Commands assume your shell is in this `platform/` directory unless otherwise noted.

---

## 0. One-time prerequisites

Skip any you already have.

```bash
# Node 20+ and pnpm (the JS workspace tool)
brew install node@20

# pnpm via the standalone installer (no sudo, no /usr/local/bin symlink dance)
curl -fsSL https://get.pnpm.io/install.sh | sh -
# adds PNPM_HOME to ~/.zshrc; either `source ~/.zshrc` or open a new shell

# Python 3.11+ and uv (you already use uv for scout/)
brew install python@3.12 uv

# Docker (easiest way to run Postgres + PostGIS) — OrbStack is a fine drop-in
brew install --cask docker          # or `brew install --cask orbstack`
open -a Docker                      # start the daemon, leave it running

# (later, only when deploying the MCP server) Cloudflare account + wrangler login
# pnpm dlx wrangler login   # opens a browser; skip until you're ready to deploy
```

> **Note on `corepack enable`**: it errors with `EACCES: permission denied` on a Homebrew Node install because corepack tries to symlink into `/usr/local/bin`. The standalone installer above sidesteps this entirely.

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
# Check first whether anything is already on 5432:
lsof -i :5432
# If a host Postgres (Homebrew, Postgres.app, etc.) is squatting on it, the
# Docker container will start but connections to localhost:5432 will hit the
# host instead. Map the container to 5433 to dodge the conflict — and update
# your .env's DATABASE_URL accordingly.

docker run --name listings-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=listings \
  -p 5433:5432 \
  -d postgis/postgis:16-3.4

# verify
docker ps   # should show listings-pg as "Up"
```

If 5432 is free on your machine, swap `-p 5433:5432` for `-p 5432:5432` and use port `5432` in `.env`. The schema/seed commands below use `docker exec` so the host port doesn't matter for those.

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
# if you mapped Postgres to 5433, update DATABASE_URL accordingly:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5433/listings
```

Open `platform/.env` and confirm the host/port match step 2.

The `ANTHROPIC_API_KEY` line can stay empty — the recommender falls back to rule-based ranking when it's unset.

> **Always also drop the env into `apps/website/.env.local`**. Next.js loads `.env*` from the app directory, not the workspace root. The workspace `.env` won't be picked up — you'll see `Error: DATABASE_URL is not set` thrown at module-load time. Solution:
>
> ```bash
> cp .env apps/website/.env.local
> ```

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
uv sync --extra dev      # `--extra dev` pulls pytest + ruff + mypy too

uv run scrape list       # registered adapters (just `example` for now)

# the example adapter expects an "example" venue row — add one before running:
docker exec listings-pg psql -U postgres -d listings -c \
  "INSERT INTO venues (slug, name, neighbourhood, category, website)
   VALUES ('example', 'Example Venue', 'Test', 'fringe', 'https://example.com/')
   ON CONFLICT (slug) DO NOTHING;"

# uv run does NOT auto-load .env — pass DATABASE_URL inline:
DATABASE_URL='postgresql://postgres:postgres@localhost:5433/listings' \
  uv run scrape venue example
```

The `example` adapter's `parse()` finds nothing on example.com, so `shows_found=0` is the correct outcome — what you're verifying is that the HTTP fetch (Scrapling), parse, and writer (`scrape_runs` row) all wire up cleanly.

Real venues come later by porting from `scout/adapters/`. See `apps/scrapers/README.md` for the mechanical port checklist.

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

Smoke-test the MCP protocol itself with the `initialize` handshake:

```bash
curl -s -X POST http://localhost:8787/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}'
```

Should print a Server-Sent Event with the server's name and capabilities. If you get `"Could not find McpAgent binding for MCP_OBJECT"`, double-check `wrangler.toml`'s Durable Objects block uses `name = "MCP_OBJECT"` — that's the name `agents/mcp` looks up by default.

---

## 9. Connect Claude Desktop to your local MCP server

Edit (create if missing):

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "theatre-scout": {
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
{ "mcpServers": { "theatre-scout": { "url": "http://localhost:8787/mcp" } } }
```

---

## 10. Run the test suite

```zsh
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
