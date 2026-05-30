# Management Playbook

Operations reference for the four external services that run **Anywhere But West End** in production: **GitHub** (source code + CI cron), **Vercel** (website), **Neon** (database), and **Cloudflare** (MCP agent).

This is the doc you reach for when:

- Something is down and you need to know which dashboard to open.
- A bill arrives and you want to know what you're paying for.
- You need to rotate a secret, change a domain, or hand the project off.

For developer onboarding see [SETUP.md](SETUP.md). For first-time deploy see [DEPLOY.md](DEPLOY.md). For an end-user/admin tour see [USER_GUIDE.md](USER_GUIDE.md).

---

## 0. At a glance

```
   ┌─────────────────────────────────────────────────────────────────────┐
   │  GitHub  (ruiboom/theatre-scout — public)                           │
   │  · source of truth for all code                                     │
   │  · push to main → Vercel auto-deploys website                       │
   │  · Actions cron 05:00 UTC → runs scrape.yml → writes to Neon        │
   │  · Actions API ← /admin "Refresh" button triggers manual run        │
   └────┬───────────────────────────────────────────────────┬────────────┘
        │ deploy on push                                    │ workflow_dispatch (PAT)
        ▼                                                   ▲
   ┌────────────────────┐    ┌────────────┐    ┌────────────────────────┐
   │  Vercel (Next.js)  │◀──▶│   Neon     │    │  Cloudflare Workers    │
   │  Website + Admin   │    │ Postgres   │    │  MCP server            │
   │  + Internal API    │    │  + PostGIS │    │  (no DB access)        │
   └─────┬──────────────┘    └────────────┘    └─────┬──────────────────┘
         │ HTTP /api/v1/*                            │ HTTP /api/v1/*
         └───────────────────────────────────────────┘
```

| What | Where | URL |
|------|-------|-----|
| Source code | GitHub (public) | <https://github.com/ruiboom/theatre-scout> |
| Scraper cron + manual trigger | GitHub Actions | <https://github.com/ruiboom/theatre-scout/actions> |
| Public website + admin + Internal API | Vercel | <https://theatre-scout.fun> |
| Database | Neon | console at <https://console.neon.tech> |
| MCP server | Cloudflare Workers | `https://platform-mcp-server.<account>.workers.dev/mcp` |

---

## 1. Vercel — Website + Admin + Internal API

### 1.1 What runs here

The entire `apps/website` Next.js 15 app, including:

- All public pages — `/`, `/shows`, `/shows/[slug]`, `/venues/[slug]`, `/about`.
- Admin CMS — `/admin/login`, `/admin`.
- Internal API — `/api/v1/*` (read endpoints for shows/venues/whats-on/recommend, the analytics events endpoint, and the admin-only refresh endpoint).
- OpenAPI export — `/api/openapi`.
- Tracked redirect — `/r`.

Every page is `force-dynamic` — no ISR, no edge caching. Each request hits Neon through the pooled connection.

### 1.2 URLs

- **Production (primary):** <https://theatre-scout.fun> — the custom domain, set as **primary** in Vercel. The apex serves the app directly; `www` redirects to it. DNS setup + hard-won lessons are in §6.
- **Vercel domain:** <https://theatre-scout-zunz.vercel.app> still works as an alias (it's the underlying project domain). A few configs haven't been migrated and still reference it — see §6.2.
- **Preview deploys:** Vercel auto-generates `https://theatre-scout-zunz-git-<branch>-<scope>.vercel.app` for every branch push (tied to the project name, not the custom domain).

> ⚠️ **Two Vercel projects deploy this repo — consolidation pending.** Alongside the
> canonical `theatre-scout-zunz` above, a duplicate project **`theatre-scout`**
> (<https://theatre-scout.vercel.app>) is also connected to the GitHub repo and
> auto-deploys from `main` on every push, serving identical content. It's almost
> certainly a second accidental import — Vercel appends the `-zunz` suffix when the
> project name is already taken — and nothing in the repo references it. Risks: 2×
> build minutes and **env/secret drift** (a `DATABASE_URL` rotation applied to only one
> project leaves the other live on a stale connection string). **To fix:** confirm
> `theatre-scout` has no custom domain or unique env vars, then disconnect or delete it
> in the Vercel dashboard, leaving `theatre-scout-zunz` as the sole project. **Until
> then, apply every env-var change to _both_ projects. Do not re-import the repo** —
> that just spawns another duplicate.

### 1.3 Project settings

- **Framework preset:** Next.js (auto-detected).
- **Root directory:** `platform/apps/website`. The monorepo lives at the repo root; Vercel needs the website subdirectory explicitly.
- **Install command:** `pnpm install` (from monorepo root).
- **Build command:** `pnpm --filter website build` or the Next.js default if root directory is set correctly.
- **Output:** `.next` (default).
- **Node version:** controlled by `.nvmrc` at `platform/.nvmrc`.

### 1.4 Environment variables (Production)

Set under **Project → Settings → Environment Variables → Production**. After changes you must redeploy — Next.js bundles env at build time for server functions.

| Name | Required | Value source |
|------|----------|--------------|
| `DATABASE_URL` | yes | Neon **pooled** connection string (ends `-pooler.neon.tech`). |
| `NEXT_PUBLIC_SITE_URL` | recommended | The canonical site URL (Vercel domain or custom domain). |
| `ADMIN_PASSWORD` | yes for admin | Strong password. Never commit. |
| `GITHUB_TOKEN` | for refresh button | Fine-grained PAT — see §5. |
| `GITHUB_REPO` | optional | Defaults `ruiboom/theatre-scout`. |
| `GITHUB_WORKFLOW` | optional | Defaults `scrape.yml`. |
| `ANTHROPIC_API_KEY` | optional | Future LLM recommender. |

Preview environments can share the same values, or use a read-only Neon branch — see Neon §2.4.

### 1.5 Pricing

- **Hobby tier** ($0/mo) is what the project ships on. Hobby is non-commercial; if monetised, upgrade to Pro ($20/mo per member).
- Bandwidth and function execution limits on Hobby: 100 GB bandwidth, 100 GB-hours function execution. Easy to stay under at current traffic.
- Watch the **Usage** tab in the Vercel dashboard.

### 1.6 Operations

| Task | How |
|------|-----|
| Deploy | Push to `main`. Vercel auto-deploys. |
| Roll back | Vercel dashboard → Deployments → previous deploy → "Promote to Production". |
| View logs | Dashboard → Deployments → click the deploy → "Functions" or "Build logs". For live traffic, `vercel logs theatre-scout-zunz` from CLI. |
| Add env var | Settings → Environment Variables → add → **redeploy** (env changes don't apply to running functions). |
| Add custom domain | Settings → Domains → add → follow DNS instructions → set `NEXT_PUBLIC_SITE_URL` to match → redeploy. |
| Rotate `ADMIN_PASSWORD` | Update env var → redeploy. Existing admin cookies will fail the next check and force a fresh login. |

### 1.7 Failure modes

- **502 / function timeout:** Neon connection pool exhausted, or a slow query. Check Neon dashboard for active connections; verify `DATABASE_URL` is the pooled URL.
- **"0 shows" on the homepage:** DB is empty or scraper is failing. Check `/admin` for scrape status, or GitHub Actions runs.
- **Refresh button does nothing:** `GITHUB_TOKEN` missing or wrong scope. See §5.

---

## 2. Neon — Postgres database

### 2.1 What runs here

A single Postgres 16 database with PostGIS and `pg_trgm` extensions. Tables: `venues`, `shows`, `performances`, `tags`, `show_tags`, `scrape_runs`, `events`. Schema canonically lives in `packages/db/schema.sql` in the repo.

### 2.2 URLs

- **Console:** <https://console.neon.tech>
- **Project page:** Neon console → choose project (named e.g. `theatre-scout` or `listings`).
- **Connection strings:** Console → project → **Connection Details**. Two important forms:

| Form | Use for | Hostname pattern |
|------|---------|------------------|
| **Pooled** | Vercel (serverless), MCP server (if it ever talked to DB) | `ep-*-pooler.<region>.aws.neon.tech` |
| **Direct** | Scrapers, manual `psql`, migrations, `etl_from_scout.py` | `ep-*.<region>.aws.neon.tech` |

The difference matters: pooled goes through PgBouncer (transaction-pooled, short-lived connections — perfect for serverless), direct gives you a long-lived session with full Postgres features. The scraper bulk-upsert path needs direct.

### 2.3 Extensions

Both must be installed (one-time per database):

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Used by: PostGIS for `GEOGRAPHY(POINT, 4326)` and `ST_DWithin` (geo queries); pg_trgm for fuzzy venue name matching.

### 2.4 Branches

Neon supports git-style branches of the database. Useful for:

- A `preview` branch for Vercel preview deployments (cheap, throwaway, snapshot of prod data).
- A `dev` branch for trying schema migrations safely.

The free tier covers a handful of branches and the working set we use. Branch lifecycle: console → project → Branches → "New branch".

### 2.5 Pricing

- **Free tier** — 0.5 GB storage, 1 always-on compute, autosuspends after inactivity. Comfortable headroom for this project.
- Cost spikes typically come from **compute hours** when something stays connected. The scrapers run for ~17 minutes a day; the website on Vercel uses the pooler so connections are short-lived. Both are fine.
- Storage is small — show data + events table at current write rate stays well under 100 MB.

### 2.6 Operations

| Task | How |
|------|-----|
| Apply schema | `psql "$DATABASE_URL_DIRECT" -f platform/packages/db/schema.sql` |
| Apply migration | `psql "$DATABASE_URL_DIRECT" -f platform/packages/db/migrations/000X_*.sql` |
| Manual query | `psql "$DATABASE_URL_DIRECT"` (use direct URL to avoid pooler quirks for interactive use) |
| Snapshot data | Neon console → Backups (point-in-time recovery on paid; manual `pg_dump` on free) |
| Rotate password | Console → project → Roles → reset password → update `DATABASE_URL` on Vercel (**both projects** until the duplicate is removed — see §1.2) and `NEON_DATABASE_URL` secret on GitHub → redeploy Vercel |
| Inspect events / scrape status | `select * from scrape_runs order by started_at desc limit 20;` |

### 2.7 Failure modes

- **`SSL connection required`:** make sure the connection string includes `?sslmode=require`. Neon enforces TLS.
- **`too many connections`:** you're using direct URL where pooled belongs, or a serverless function isn't closing connections. Switch Vercel to pooled.
- **Slow first request after idle:** Neon's compute autosuspends when idle and takes ~500 ms to wake. Acceptable for a small site; can be disabled on paid tier.

---

## 3. Cloudflare Workers — MCP server

### 3.1 What runs here

`apps/mcp-server` — a single Worker exposing six MCP tools and an OpenAPI spec. **Stateless from a data point of view**: it only proxies HTTP calls to the Vercel-hosted Internal API. It does **not** open a connection to Neon. The Durable Object (`ListingsMCP`) is only used by the MCP framework to hold per-client streaming sessions.

### 3.2 URLs

- **Dashboard:** <https://dash.cloudflare.com>
- **Account → Workers & Pages → `platform-mcp-server`**
- **Production endpoints:**
  - MCP transport: `https://platform-mcp-server.<account>.workers.dev/mcp`
  - OpenAPI: `https://platform-mcp-server.<account>.workers.dev/openapi.json`
  - Health: `https://platform-mcp-server.<account>.workers.dev/health`

`<account>` is your Cloudflare account's `workers.dev` subdomain (set once when you enabled Workers).

### 3.3 Configuration

Lives in `apps/mcp-server/wrangler.toml`:

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

The `API_BASE_URL` var is the default. Override per-environment using `wrangler secret put API_BASE_URL` — secrets override vars and are not committed.

### 3.4 Pricing

- **Workers Free** — 100,000 requests/day per account, unlimited duration up to 10 ms CPU per request. Plenty for an MCP proxy.
- **Durable Objects** — included on Workers Free at small volume (50,000 reads/day, 100,000 writes/day). Each MCP session uses a few DO ops; nowhere near the cap.
- Watch usage at Dashboard → Workers & Pages → Plans.

### 3.5 Operations

| Task | How (from `apps/mcp-server`) |
|------|------------------------------|
| Deploy | `wrangler deploy` |
| Local dev | `pnpm dev` (uses `wrangler dev` → http://localhost:8787) |
| Set / rotate `API_BASE_URL` secret | `wrangler secret put API_BASE_URL` |
| List secrets | `wrangler secret list` |
| Tail logs | `wrangler tail` |
| Roll back | `wrangler rollback` (Cloudflare keeps recent deploys) |
| Attach custom domain | Dashboard → Workers → service → Triggers → Custom Domains → add. Requires the apex domain in Cloudflare DNS. |

### 3.6 Client wiring

For **Claude Desktop**, add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or the equivalent on Windows/Linux:

```json
{
  "mcpServers": {
    "anywhere-but-west-end": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://platform-mcp-server.<account>.workers.dev/mcp"
      ]
    }
  }
}
```

Restart Claude Desktop. The six tools should appear. The tool names (`search_shows`, `get_show`, `whats_on`, `recommend_shows`, `search_venues`, `get_venue`) match what's in [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md).

For the **Custom GPT**: paste `https://theatre-scout.fun/api/openapi` (or `<MCP-URL>/openapi.json` — they're equivalent) into the Actions config at <https://chatgpt.com/gpts/editor>.

### 3.7 Failure modes

- **`Tool error: 5xx` from MCP client:** the worker is up but the API is down or the URL is wrong. `wrangler tail` to see the actual fetch error. Verify `API_BASE_URL` secret with `wrangler secret list`.
- **Cold-start latency:** Workers cold-start in ~5 ms — usually invisible. If MCP tool calls feel slow, the latency is in the Vercel function or Neon query, not the worker.
- **Durable Object errors after a deploy:** the migration `tag = "v1"` in `wrangler.toml` is one-shot. Don't re-tag; add a new migration block for any future DO class changes.

---

## 4. GitHub — Source, CI, and cron

GitHub does three jobs for this project: it stores the source code, it runs the daily scrape on Actions, and it's the trigger surface for both Vercel deploys (via the GitHub App) and the admin Refresh button (via the REST API).

### 4.1 The repository

- **URL:** <https://github.com/ruiboom/theatre-scout>
- **Owner:** `ruiboom`
- **Visibility:** **Public**. Source, issues, PRs, and the Actions log are all publicly readable; anyone with a GitHub account can file an issue. Practical implications:
  - GitHub Actions on a public repo gets unlimited free standard-runner minutes — no usage quota or billing concern for the daily scrape.
  - Because the repo is public, **nothing secret may ever be committed.** Sensitive material lives only in Actions secrets and the platforms' own secret stores — never in git history. Sanity-check any new file for credentials before committing.
- **Default branch:** `main`. All deploys and cron runs key off `main`.
- **Description:** "Anywhere But The West End — a multi-surface listings platform for London's 70 non-West End theatres. Scout/ is the live site; platform/ is the v2 architecture (Postgres + Internal API + Next.js + MCP server)."

### 4.2 Branching and deploy flow

There is no fixed branching policy — small project, single committer. The convention is:

- Work on a feature branch (`<scope>/<short-name>`, e.g. `fix/almeida-adapter`).
- Push the branch — Vercel auto-creates a **preview deployment** at a generated URL.
- Open a PR for visibility (optional — direct pushes to `main` are also acceptable for solo work).
- Merge to `main` (or push directly) — Vercel auto-deploys to production.

The Vercel ↔ GitHub link is handled by the **Vercel GitHub App**, installed once on the `ruiboom` GitHub account against this repo. No deploy hook is configured — pushes trigger deploys automatically through the app.

### 4.3 Workflows

Only one workflow exists at `.github/workflows/scrape.yml`:

| Trigger | Source |
|---------|--------|
| `schedule: cron: "0 5 * * *"` | GitHub cron — daily at 05:00 UTC. Cron does not shift for DST → lands at 05:00 GMT in winter, 06:00 BST in summer. |
| `workflow_dispatch` | Manual: Actions tab → "Daily scrape" → "Run workflow". |
| `workflow_dispatch` via API | The admin "Refresh data" button on `/admin` calls `POST https://api.github.com/repos/ruiboom/theatre-scout/actions/workflows/scrape.yml/dispatches` with `ref=main`. |

The workflow:

- **Name:** "Daily scrape"
- **Concurrency:** `group: scrape, cancel-in-progress: false` — overlapping runs queue rather than collide.
- **Permissions:** `contents: read` only (no write back to the repo).
- **Working dir:** `platform/apps/scrapers` (the Python ingestion package).
- **Runner:** `ubuntu-latest`, 45-minute timeout.
- **Cache:** Patchright/Chromium at `~/.cache/ms-playwright` (key `playwright-${{ runner.os }}-v1`) — the 250 MB Chromium download is paid once until the cache is invalidated.

Steps (in order):

1. Checkout
2. `astral-sh/setup-uv@v4` with `uv.lock` caching
3. Cache Patchright browsers
4. `uv sync`
5. `uv run scrapling install` (Chromium)
6. `uv run scrape sync-venues ../../../theatres.yaml`
7. `uv run scrape all --enrich --replace --workers 16`
8. Smoke test (only if `vars.SITE_BASE_URL` is set): `curl "$SITE_BASE_URL/api/v1/shows?limit=1"` and assert `total > 100`.

Typical wall time: ~17 minutes. Data is current by 05:20 UTC.

### 4.4 Actions secrets vs variables

Repo → **Settings → Secrets and variables → Actions**. Two distinct stores:

| Kind | Name | Value | Used by |
|------|------|-------|---------|
| **Secret** | `NEON_DATABASE_URL` | Neon **direct** (non-pooled) connection string with `?sslmode=require` | The scraper job's `DATABASE_URL` env. |
| **Variable** | `SITE_BASE_URL` | `https://theatre-scout-zunz.vercel.app` | The post-scrape smoke test step (`vars.SITE_BASE_URL`). |

Secrets are write-only after creation and never echoed in logs; variables are plaintext and visible in run logs. `SITE_BASE_URL` is non-sensitive (it's literally the public website URL), so it lives as a variable.

If you move the site to a custom domain, update `SITE_BASE_URL` here and the smoke test will follow.

### 4.5 The refresh button wiring (Vercel ↔ GitHub)

The admin **Refresh data** button on `/admin` calls `POST /api/v1/admin/refresh`, which on the server side fetches:

```
POST https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches
Authorization: Bearer {GITHUB_TOKEN}
Content-Type: application/json

{"ref": "main"}
```

For this to work:

1. **`GITHUB_TOKEN`** must be set on Vercel (Project → Settings → Environment Variables → Production).
2. The token must be a **fine-grained PAT**:
   - Generate at <https://github.com/settings/personal-access-tokens>.
   - **Resource owner:** `ruiboom` (the GitHub account that owns the repo).
   - **Repository access:** Only select repositories → `ruiboom/theatre-scout`.
   - **Repository permissions:** Actions → **Read and write**. (Metadata read is auto-included.)
   - **Expiration:** 90 days is recommended — GitHub will email a reminder before it lapses.
3. `GITHUB_REPO` (default `ruiboom/theatre-scout`) and `GITHUB_WORKFLOW` (default `scrape.yml`) on Vercel must match the actual repo and workflow filename.

Classic PATs also work but grant far broader access — use fine-grained.

After rotating, **redeploy** Vercel (env changes don't apply to running serverless functions until a new build is shipped).

### 4.6 GitHub Apps installed

| App | Purpose | Where to manage |
|-----|---------|-----------------|
| **Vercel** | Deploy on push, status checks on PRs, preview URL comments | <https://github.com/settings/installations> → Vercel → Configure |
| **Neon (optional)** | Database preview branches per PR | Not installed by default. Useful if you start running schema migrations against preview branches; see Neon §2.4. |

No webhooks are configured directly on the repo — both apps use GitHub App installations, which is the modern equivalent and doesn't need any per-repo setup once the app is installed.

### 4.7 Operations

| Task | How |
|------|-----|
| See cron history | Actions tab → "Daily scrape" → recent runs. |
| Manually run a scrape | Actions tab → "Daily scrape" → "Run workflow" → branch `main`. Or use the admin Refresh button. |
| Re-run a failed scrape | Actions tab → failed run → "Re-run all jobs" (or "Re-run failed jobs" if it was partial). |
| Pause the cron | Actions tab → "Daily scrape" → "···" → "Disable workflow". Re-enable from the same menu. |
| Add a collaborator | Settings → Collaborators → "Add people". |
| Rotate `NEON_DATABASE_URL` (Actions secret) | Settings → Secrets and variables → Actions → secrets → Update. No redeploy needed; next run picks it up. |
| Change `SITE_BASE_URL` (Actions variable) | Same screen, variables tab. |
| Add a new venue | Edit `theatres.yaml` (repo root) + add `platform/apps/scrapers/scrapers/adapters/<slug>.py` + register it in `adapters/__init__.py`. Push. Next cron run (or manual dispatch) picks it up. |
| Inspect logs | Click into a run → expand each step. The "Scrape all venues into Neon" step has per-venue progress. |

### 4.8 Failure modes

- **Run fails at the database step:** `NEON_DATABASE_URL` is stale (Neon password rotated, branch deleted?). Update the GitHub secret.
- **Patchright/Chromium download timeout:** the cache key is invalidated or the network step flaked. Re-running usually works; expect ~250 MB of download time on the first run after a cache miss.
- **Smoke test fails (`total > 100` assertion):** the scrape technically completed but produced too few shows. Likely a regression in one or more adapters; inspect per-venue logs in the "Scrape all venues into Neon" step output for `failed` rows.
- **Cron didn't fire:** GitHub auto-disables scheduled workflows on repos with no recent activity (60 days). Push any commit, or trigger a manual dispatch to reset the clock.
- **Refresh button returns an error:** GitHub returns `422` if the workflow can't be found (check `GITHUB_REPO` / `GITHUB_WORKFLOW` env vars on Vercel), `403` if the PAT is missing or under-scoped (check `GITHUB_TOKEN`), `401` if the PAT has expired (regenerate).

---

## 5. Secrets and config inventory

What lives where. Rotate annually, or sooner on any suspected leak.

| Item | Sensitive? | Stored in | Used by | How to rotate / change |
|------|------------|-----------|---------|------------------------|
| Neon password (pooled URL) | yes | Vercel env: `DATABASE_URL` | Website | Reset in Neon → update on Vercel → redeploy |
| Neon password (direct URL) | yes | GitHub Actions secret: `NEON_DATABASE_URL` | Scrapers (CI) | Reset in Neon → update GitHub secret |
| `ADMIN_PASSWORD` | yes | Vercel env | Admin login | Update on Vercel → redeploy → log in again |
| `GITHUB_TOKEN` (PAT) | yes | Vercel env | Refresh button | Re-issue PAT → update on Vercel → redeploy |
| `API_BASE_URL` | no (public URL) | Cloudflare Worker secret | MCP server | `wrangler secret put API_BASE_URL` |
| `SITE_BASE_URL` | no | GitHub Actions **variable** | Scrape smoke test | Settings → Variables → edit |
| `GITHUB_REPO` / `GITHUB_WORKFLOW` | no | Vercel env (defaults exist) | Refresh button | Update on Vercel → redeploy |
| `NEXT_PUBLIC_SITE_URL` | no | Vercel env | OpenAPI export, metadata | Update on Vercel → redeploy |
| `ANTHROPIC_API_KEY` (optional) | yes | Vercel env | Future LLM recommender | Re-issue at console.anthropic.com |

Nothing else is configured. The Neon connection strings and the admin password are the only truly sensitive items.

---

## 6. Domain / DNS

**Live custom domain: <https://theatre-scout.fun>** — registrar + DNS at **Hover**, set as the **primary** domain in Vercel. The Cloudflare MCP server is still on its auto-issued `platform-mcp-server.<account>.workers.dev` domain.

### 6.1 How `theatre-scout.fun` is wired (the working setup)

DNS at Hover (TTL 15 min):

| Type | Host | Value | Purpose |
|------|------|-------|---------|
| `A` | `@` | `216.198.79.1` | apex → Vercel (serves the app) |
| `A` | `www` | `216.198.79.1` | `www` → Vercel |
| `MX` | `@` | `10 mx.hover.com...` | email — leave alone |

In Vercel → Domains, `theatre-scout.fun` is **primary** (apex serves the app directly) and `www` redirects to the apex. Vercel auto-issues the TLS certs once the records resolve.

**Lessons (these cost an afternoon — don't repeat):**
- **Don't use Hover's "URL forwarding"** (FORWARDS tab). It's HTTP-only — port 443 has no cert, so `https://` just times out. Point DNS at Vercel instead.
- **Hover wouldn't persist a `CNAME` on `www`** — the add silently never reached its nameservers, and a CNAME colliding with a leftover/wildcard record returns `SERVFAIL`. An **A record to Vercel's IP** (`216.198.79.1`) works and Vercel accepts it for `www`.
- **No wildcard `A *`** — it injects an A for every host and collides with any per-host CNAME, breaking that host.
- Making the **apex primary** got the site live immediately off the already-valid apex cert, decoupling launch from the `www` gymnastics.

### 6.2 Still on the `.vercel.app` domain (migrate when ready)

These were **not** switched to the custom domain and still point at `theatre-scout-zunz.vercel.app`:

- **Vercel env `NEXT_PUBLIC_SITE_URL`** → set to `https://theatre-scout.fun` and redeploy, so canonical URLs / OpenGraph / the `/api/openapi` `servers` block use it.
- **MCP worker secret `API_BASE_URL`** → `wrangler secret put API_BASE_URL` = `https://theatre-scout.fun/api/v1`.
- **GitHub Actions variable `SITE_BASE_URL`** (post-scrape smoke test).
- **`apps/mcp-server/server.json` `websiteUrl`** and the **`/api/openapi` fallback** in `app/api/openapi/route.ts` (a code default, harmless once the env var is set).

### 6.3 Attaching a *different* / additional domain

To attach another custom domain (e.g. `anywherebutwestend.com`):

1. **Register and host DNS** in Cloudflare (recommended — gives free CDN and clean integration with Workers).
2. **Vercel website:**
   - Vercel project → Settings → Domains → add `anywherebutwestend.com` and `www.anywherebutwestend.com`.
   - Vercel will give DNS instructions. In Cloudflare DNS, add the records (typically a CNAME for `www` and an apex flattening A or `CNAME` to Vercel).
   - Set DNS proxy to **DNS only** (grey cloud) on the Vercel-pointing records — Vercel needs to terminate TLS.
   - Update env vars: `NEXT_PUBLIC_SITE_URL=https://anywherebutwestend.com`. Redeploy.
3. **MCP server:**
   - Cloudflare dashboard → Workers → `platform-mcp-server` → Triggers → Custom Domains → add `mcp.anywherebutwestend.com`.
   - Cloudflare auto-creates the DNS record because the zone is in the same account.
   - Update the worker secret: `wrangler secret put API_BASE_URL` → `https://anywherebutwestend.com/api/v1`.
4. **Update clients:**
   - Claude Desktop config → swap to `https://mcp.anywherebutwestend.com/mcp`.
   - Custom GPT actions → swap OpenAPI URL.

---

## 7. Routine operations

### Daily

- Nothing required. Cron handles the scrape. Eyeball `/admin` if convenient.

### Weekly

- Skim `/admin` — visit trends, top searches.
- Check Vercel Usage tab — bandwidth + function execution.

### Monthly

- Glance at Neon storage + compute hours.
- Glance at Cloudflare Workers requests.
- Review GitHub Actions usage minutes (free quota is generous; mostly informational).

### When deploying changes

1. Push to a branch → Vercel auto-creates a preview deploy.
2. Open the preview URL → smoke test.
3. Merge to `main` → production deploy.
4. If env vars changed, **redeploy** (env updates don't reapply automatically to running functions).

### Adding a new theatre

1. Edit `theatres.yaml` at repo root — add the venue with a kebab-case slug.
2. Save a representative HTML sample to `tests/fixtures/<slug>.html`.
3. Try the generic adapter first — add a tuple in `apps/scrapers/scrapers/adapters/bulk.py`.
4. If generic fails, write a bespoke adapter in `apps/scrapers/scrapers/adapters/<slug>.py`.
5. Add a parse test in `apps/scrapers/tests/adapters/test_<slug>.py`.
6. Push. Either wait for the 05:00 UTC cron, or click **Refresh data** on `/admin`.

### Handing the project off

1. **GitHub** — transfer the repo: Settings → General → Danger Zone → "Transfer ownership". Alternatively, add the new owner as a collaborator (Settings → Collaborators → Add people → Admin role) and leave ownership with you. After transfer, the new owner must re-install the Vercel GitHub App on the repo under their account.
2. **Vercel** — Vercel project → Settings → General → Transfer Project. The new owner needs the Vercel GitHub App installed and access to the GitHub repo.
3. **Neon** — invite the new owner to the Neon project (Console → project → Settings → Sharing) or transfer ownership.
4. **Cloudflare** — Workers can be deployed under a different account by changing the `name` in `wrangler.toml` and re-running `wrangler deploy` against the new account. Or invite to the existing account (Dashboard → Members) and keep the worker name.
5. **Secrets** — generate fresh ones on each platform (new Neon passwords, new admin password, new fine-grained PAT in the new owner's GitHub, new `API_BASE_URL` worker secret if anything changed). Don't hand over old creds.
6. **GitHub Actions secrets** — if the repo is transferred, secrets follow it automatically. If you instead clone the repo to a new owner, re-create `NEON_DATABASE_URL` (secret) and `SITE_BASE_URL` (variable) in the new repo.

---

## 8. Cost summary (as of 2026)

| Service | Plan | Monthly cost |
|---------|------|--------------|
| GitHub | Free (public repo, single user) | $0 |
| GitHub Actions | Public repo → unlimited free standard-runner minutes (the daily scrape is ~17 min/day) | $0 |
| Vercel | Hobby (non-commercial) | $0 |
| Neon | Free (0.5 GB, 1 always-on compute) | $0 |
| Cloudflare Workers | Free (100k req/day) | $0 |
| **Total** | | **$0/mo** at current scale |

If the project monetises or outgrows free tiers:

- **GitHub Team** $4/user/mo — not needed for a one-person project; branch protection and required reviews are free on public repos anyway.
- **Vercel Pro** $20/mo per member (commercial use, higher limits).
- **Neon Launch** $19/mo (more storage, more compute hours, larger branch tree).
- **Cloudflare Workers Paid** $5/mo (10M requests included; covers any conceivable MCP usage).

Realistic next-step total: ~$45/mo when growing past the free tiers.

---

## 9. Quick reference card

| I need to... | Go to... |
|--------------|----------|
| Check if the site is up | <https://theatre-scout.fun> |
| Open the repo | <https://github.com/ruiboom/theatre-scout> |
| Look at last-run scrape | <https://github.com/ruiboom/theatre-scout/actions/workflows/scrape.yml> |
| Trigger a scrape | `/admin` on the site, or Actions tab → "Daily scrape" → "Run workflow" |
| Read DB directly | `psql` with the Neon **direct** URL |
| Update the website | Push to `main` on GitHub (Vercel auto-deploys) |
| Update the scraper | Push to `main` on GitHub (next 05:00 UTC run uses new code, or trigger manually) |
| Update the MCP server | `cd platform/apps/mcp-server && wrangler deploy` |
| Rotate `ADMIN_PASSWORD` | Vercel env → edit → redeploy |
| Rotate `GITHUB_TOKEN` (PAT) | <https://github.com/settings/personal-access-tokens> → re-issue → Vercel env → redeploy |
| Rotate `NEON_DATABASE_URL` | GitHub repo → Settings → Secrets → Actions → update |
| Add a GitHub collaborator | Repo → Settings → Collaborators → Add people |
| Add a venue | Edit `theatres.yaml` + add adapter + push |
| See site analytics | `/admin` (visits, top searches, top clicks) |
| Inspect GitHub Actions usage | <https://github.com/settings/billing> → Actions |
| Inspect Neon usage | <https://console.neon.tech> → project → Usage |
| Inspect Vercel usage | <https://vercel.com> → project → Usage |
| Inspect Cloudflare usage | <https://dash.cloudflare.com> → Workers & Pages |

---

## 10. Related docs

- [README.md](README.md) — full technical reference (architecture, code map, conventions).
- [USER_GUIDE.md](USER_GUIDE.md) — visitor and admin guide.
- [SETUP.md](SETUP.md) — local dev quick-start.
- [DEPLOY.md](DEPLOY.md) — first-time production deployment (the long form of this playbook).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture deep-dive.
- [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md) — MCP tool contract.
