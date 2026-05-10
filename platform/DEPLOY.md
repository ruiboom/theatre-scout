# Deploy

How to run the whole platform online. Each piece lands on the host that suits it — boring choices, generous free tiers.

```
                 ┌────────────────────────┐
                 │  Cloudflare Workers     │   apps/mcp-server
                 │  https://…workers.dev   │   $0–5 /mo
                 │  /mcp                   │
                 └────────────┬────────────┘
                              │  HTTPS
                              │
┌─────────────────────────────▼─────────────────────────────┐
│             Vercel (Next.js, edge + serverless)            │
│  https://your-domain.com                                   │
│  /                  public site                            │
│  /api/v1/*          Internal API                           │   $0
└─────────────────────────────┬─────────────────────────────┘
                              │  postgres-js
                              │
                  ┌───────────▼────────────┐
                  │  Neon (or Supabase)     │   $0 free tier
                  │  Postgres 16 + PostGIS  │
                  └───────────▲────────────┘
                              │
┌─────────────────────────────┴─────────────────────────────┐
│  GitHub Actions (cron)                                     │   $0
│  uv run scrape all                                         │
└────────────────────────────────────────────────────────────┘
```

**Total cost at low traffic: $0/mo.** Vercel/Neon/Cloudflare Workers/GitHub Actions all have free tiers that comfortably cover an early-stage listings site. You'll start paying when traffic or scrape frequency grows past free-tier thresholds — see the costs section at the end.

---

## Order of operations

0. Push the repo to GitHub (prerequisite).
1. Hosted Postgres on Neon.
2. Apply schema + seed to the hosted DB.
3. Deploy the website + API to Vercel.
4. Deploy the MCP server to Cloudflare Workers.
5. Schedule the scrapers on GitHub Actions.
6. (Optional) Custom domains.
7. Repoint Claude clients at the live MCP URL.

---

## 0. Get the code on GitHub

```bash
# from the worktree root
git push -u origin HEAD
gh pr create --fill && gh pr merge --squash
```

…or just push a branch and merge in the UI. Vercel and GitHub Actions both wire up to the repo — Cloudflare Workers can be deployed from your laptop, no CI needed.

---

## 1. Hosted Postgres on Neon

Neon is serverless Postgres with PostGIS, scale-to-zero, and connection pooling baked in — the right shape for Vercel's serverless model.

1. Sign up at <https://neon.tech/> and create a project.
   - Region: `London (eu-west-2)` for lowest latency from UK users.
   - Postgres version: 16.
2. **Enable PostGIS.** In the SQL editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
3. Grab two connection strings from the dashboard:
   - **Pooled** (`…-pooler.…neon.tech`) — for the website (Vercel functions). Use this everywhere serverless.
   - **Direct** (`…neon.tech` without `-pooler`) — for one-shot scripts (`scripts/seed.sql`, scrapers).

> **Why two?** Vercel functions can spawn many concurrent connections; the pooler keeps you under Postgres' connection limit. Long-running scripts work fine on the direct URL.

### Alternative: Supabase

Same shape — sign up, create project, **Database → Extensions → enable `postgis`**, then use the **Connection Pooling** URL (port 6543) for the website and the direct URL (port 5432) for one-shots.

---

## 2. Apply the schema and seed

From `platform/`:

```bash
# Direct (non-pooled) URL works best for psql one-shots
export NEON_DIRECT_URL='postgresql://user:pass@…neon.tech/listings?sslmode=require'

psql "$NEON_DIRECT_URL" -f packages/db/schema.sql
psql "$NEON_DIRECT_URL" -f scripts/seed.sql

psql "$NEON_DIRECT_URL" -c 'SELECT slug, title FROM shows;'   # 6 rows
```

If `psql` isn't installed: `brew install libpq && brew link --force libpq`.

---

## 3. Vercel — the website + Internal API

Vercel auto-detects pnpm workspaces. You only have to point it at the right subfolder.

1. <https://vercel.com/new> → import your GitHub repo.
2. **Framework Preset:** Next.js (auto-detected).
3. **Root Directory:** `platform/apps/website` *(important — sets where Next.js lives without breaking the pnpm install at the workspace root).*
4. **Build & Output Settings:** leave defaults. Vercel will run `pnpm install` from the repo root, then `next build` in the website folder. The `transpilePackages: ['@platform/shared']` line in `next.config.ts` makes the shared package compile correctly.
5. **Environment Variables:**
   | Name | Value | Notes |
   |------|-------|-------|
   | `DATABASE_URL` | Neon **pooled** URL | the only required var |
   | `NEXT_PUBLIC_SITE_URL` | `https://your-domain.com` | optional, for canonical URLs |
6. **Deploy.** First build takes a couple of minutes; subsequent ones cache.

Verify:

```bash
curl -s https://<your-vercel-domain>/api/v1/whats-on?when=this_weekend | jq '.window, .total'
curl -s https://<your-vercel-domain>/api/v1/shows | jq '.total'
```

**Heads up — Vercel TOS:** the Hobby plan is "non-commercial only." For a side-project listings site that's fine. If you start running ads or partnership commissions, move to the **Pro plan** ($20/mo). The platform itself is host-agnostic — Fly.io, Railway, and Render all run the same Next.js app fine if you'd rather avoid Vercel.

---

## 4. Cloudflare Workers — the MCP server

The MCP server is a single Worker with a Durable Object for session storage. Deploy it from your laptop — it doesn't need GitHub integration.

```bash
cd platform/apps/mcp-server

pnpm dlx wrangler login                          # browser login, one-time

# point the worker at your live API
pnpm dlx wrangler secret put API_BASE_URL
# paste: https://your-vercel-domain.com/api/v1

pnpm dlx wrangler deploy
```

The deploy output prints the URL — something like `https://platform-mcp-server.<your-account>.workers.dev`. The MCP endpoint is at `/mcp`.

```bash
curl https://platform-mcp-server.<your-account>.workers.dev/health   # {"ok":true}
```

> **Workers free tier:** 100,000 requests/day. Plenty for a single MCP server with low usage. **Durable Objects** count separately — if traffic gets meaningful you may need the **Workers Paid plan** ($5/mo) which includes 1M DO requests. Until launch you're almost certainly free.

### Alternative: Fly.io / Railway

If you'd rather skip Cloudflare, you can run the MCP server as a long-lived Node process on Fly.io or Railway. You'd need to swap `agents/mcp` (Cloudflare-specific) for the SDK's `StreamableHTTPServerTransport` directly, and serve it with Hono. ~30 lines of change. Cloudflare is the easier path.

---

## 5. GitHub Actions — scheduled scrapers

The Python scrapers run on a cron from your repo. No infrastructure to manage.

Create `.github/workflows/scrape.yml` at the repo root:

```yaml
name: Scrape

on:
  schedule:
    - cron: "0 3 * * *"    # 3 AM UTC daily — adjust to taste
  workflow_dispatch:        # manual trigger from the Actions tab

jobs:
  scrape:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: platform/apps/scrapers
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - run: uv sync

      - run: uv run scrape all
        env:
          # Use the DIRECT (non-pooled) URL for batch jobs
          DATABASE_URL: ${{ secrets.DATABASE_URL_DIRECT }}
```

Then in **GitHub → Settings → Secrets and variables → Actions → New repository secret**:

- `DATABASE_URL_DIRECT` — Neon's direct (non-pooled) URL.

Push the workflow, then **Actions → Scrape → Run workflow** to test it manually. You should see `uv run scrape all` finish and the row count in your Neon dashboard tick up.

> **Free for public repos.** Private repos get 2,000 minutes/month free, more than enough for one daily scrape.

### Why not Vercel Cron?

Vercel Cron runs serverless functions — fine for the *trigger* but a poor fit for a multi-minute Python scrape that talks to 70 sites. Use it later if you want to schedule a *single* "send the daily newsletter" job that calls Beehiiv.

---

## 6. (Optional) Custom domains

**Vercel:** project → Settings → Domains → add your domain → follow the DNS instructions. Apex (`yoursite.com`) and `www` both work.

**Cloudflare Workers:** the worker already gets a `*.workers.dev` URL. To put it on `mcp.yoursite.com`:
1. Add `yoursite.com` as a Cloudflare zone (free).
2. **Workers & Pages → your worker → Settings → Domains & Routes → Add custom domain.**

---

## 7. Repoint Claude clients at the live MCP URL

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anywhere-but-west-end": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://platform-mcp-server.<account>.workers.dev/mcp"]
    }
  }
}
```

Restart Claude Desktop (⌘Q). Try *"what's on this weekend in Hackney under £15?"* and watch it call the live tools.

For **Claude.ai** (web): Settings → Feature Preview → Custom Connectors → add the same URL. The same MCP server serves both clients.

For the **Custom GPT**: flesh out `apps/mcp-server/src/index.ts`'s `/openapi.json` handler so it describes `/api/v1/*`, then point a Custom GPT Action at `https://platform-mcp-server.<account>.workers.dev/openapi.json`. Same backend, second storefront.

---

## What it'll cost

At pre-launch / low traffic — **$0/mo**. Realistic break points:

| Service | Free tier | First paid step |
|---------|-----------|-----------------|
| Vercel | Hobby (non-commercial) | Pro $20/mo when you take payments / heavy traffic |
| Neon | 0.5 GB storage, scale-to-zero | Launch plan $19/mo at ~5 GB or always-on |
| Cloudflare Workers | 100k req/day | Workers Paid $5/mo for Durable Objects at scale |
| GitHub Actions | 2,000 min/mo (private) | Free for public repos |

**Realistic worst case for a busy first year: $25–45/mo.** The architecture is intentionally cheap on purpose.

---

## Caveats and gotchas

- **Connection pooling matters.** Use Neon's `-pooler` URL (or Supabase's port-6543 URL) on Vercel. The direct URL on serverless will run out of connections.
- **Cold starts.** Vercel functions cold-start in ~200ms; Neon scale-to-zero adds another ~500ms on the first hit after idle. Acceptable for a listings site; budget for a `/health` warmer if you need consistent latency.
- **Postgres ICE cap on Neon free tier.** Free Neon scales to zero after 5 min idle. If you're doing live demos, keep a tab open or upgrade.
- **Logs.** Vercel logs are in the dashboard (Functions tab); Cloudflare Workers logs are in `wrangler tail` or the Workers dashboard's **Logs** tab. Stream both during launch.
- **Don't commit `.env`.** It's in `.gitignore`, but if you ever set a Neon URL locally, double-check `git status` before you push.

---

## Daily ops cheat-sheet

```bash
# Tail Vercel function logs in real time
vercel logs <your-domain>.vercel.app --follow

# Tail the Worker
cd platform/apps/mcp-server && pnpm dlx wrangler tail

# Run a manual scrape against prod (from your laptop)
cd platform/apps/scrapers
DATABASE_URL='<NEON_DIRECT_URL>' uv run scrape venue almeida

# psql into prod
psql "$NEON_DIRECT_URL"
```
