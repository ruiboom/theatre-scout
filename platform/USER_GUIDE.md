# User Guide

This is the everyday guide to using **Anywhere But West End** — the public listings site for London's 70 non-West End theatres — and to running its small admin CMS.

The product lives at **<https://theatre-scout-zunz.vercel.app>** (production Vercel URL). A custom domain may be attached later; the playbook covers that.

---

## Part 1 — For visitors (the public site)

The site is fully public. No sign-up, no login, no cookie banner. Everything is read-only browsing.

### Home page (`/`)

Lands on a venue index grouped by tier (Major, Mid-size, Fringe, Outer). Each card shows:

- Venue name and neighbourhood.
- Current show count.
- Link through to the venue page.

A hero strip at the top shows totals: how many shows are on across the city, how many venues are tracked.

### Shows index (`/shows`)

The main browsing surface. Two view modes:

- **Rails** — horizontally scrollable rows grouped by category ("Plays opening this week", "Musicals running now", "Fringe picks", etc.).
- **List** — a flat, dense list sorted by start date.

Filter chips along the top:

- **Time window** — Today, This week, This weekend, New (recently added).
- **Show type** — play, musical, comedy, dance, opera, family, cabaret.
- **Venue tier** — Major, Mid-size, Fringe, Outer.
- **Sort** — by start date, by title.

A search box runs full-text search across show title and description. Filter state is encoded into the URL, so any view is shareable as a link.

### Show detail (`/shows/<slug>`)

Everything we know about one production:

- Title, run dates, venue (links to the venue page).
- Full description.
- Performance schedule — every individual date and time, with sold-out flags where available.
- Creators — writer, director, cast.
- Content warnings, age rating, duration.
- Reviews summary (where extracted).
- **Book tickets** button — links straight to the venue's box office. This is a tracked outbound click (used purely for admin analytics — no personal data is recorded).
- Price range.

### Venue detail (`/venues/<slug>`)

Profile page for one theatre:

- Name, neighbourhood, address, nearest tube.
- Embedded Leaflet map pinned to the venue.
- Capacity, description.
- **All current shows** at this venue.
- Website link (tracked outbound).

### About (`/about`)

Static page describing the project's mission — surfacing London's non-West End theatre scene.

### What gets tracked

Three lightweight analytics events are recorded server-side, with no cookies and no identifiers:

1. **Visit** — a page was loaded.
2. **Search** — a search query was run.
3. **Outbound** — a "Book tickets" or venue-website link was clicked.

Events feed the admin dashboard only. There is no third-party tracker, no Google Analytics, no fingerprinting.

---

## Part 2 — For machines (Claude, ChatGPT, agents)

The same data is exposed through two machine surfaces. End users don't need to know about these — they're documented in [README.md](README.md) and the [Tool Surface spec](docs/TOOL_SURFACE.md).

- **MCP server** — `https://platform-mcp-server.<account>.workers.dev/mcp` — six tools (`search_shows`, `get_show`, `whats_on`, `recommend_shows`, `search_venues`, `get_venue`) usable from Claude Desktop or any MCP client.
- **OpenAPI** — `https://theatre-scout-zunz.vercel.app/api/openapi` — used to build the Custom GPT.

Both speak to the same underlying Internal API (`/api/v1/*`) — agents and humans see the exact same data.

---

## Part 3 — For the admin

The admin area is **password-only**. There is one admin account, controlled by the `ADMIN_PASSWORD` environment variable. Sessions are cookie-based (HTTP-only, 14-day lifetime, SHA-256 hash, Secure in production).

### Logging in (`/admin/login`)

1. Visit **<https://theatre-scout-zunz.vercel.app/admin/login>**.
2. Enter the admin password.
3. On success you're redirected to `/admin`. On failure the form shows a generic error.

Log out with the **Log out** button on the dashboard. The cookie is cleared immediately.

If `ADMIN_PASSWORD` is unset on the server, `/admin` returns a 500 — by design, so you can't accidentally ship an unprotected admin.

### Dashboard (`/admin`)

Single-screen overview, refreshed each request.

#### Traffic

| Metric | Window |
|--------|--------|
| Visits | 24 h, 7 d, 30 d |
| Top 10 searches | last 7 days |
| Top 10 venue clicks | last 7 days |
| Top 10 outbound show clicks (i.e. tickets clicked) | last 7 days |

"Venue click" = a visit to `/venues/<slug>`. "Outbound show click" = a "Book tickets" link followed via `/r`.

#### Scrape status

- **Last run** — date, time, duration.
- **Successes vs failures** — per-venue tally from the most recent run.
- **Any errors** — exception messages from adapters that failed.

#### Refresh data (manual scrape trigger)

Big button: **Refresh data**.

- Calls `POST /api/v1/admin/refresh`, which uses the configured GitHub PAT to dispatch the `scrape.yml` workflow on `ruiboom/theatre-scout`.
- The scrape runs on GitHub Actions, not on Vercel — Vercel just kicks it off.
- A full run takes ~17 minutes. The dashboard does not block on it. To check progress, watch the GitHub Actions tab on the repo.
- Data is refreshed automatically every day at **05:00 UTC** by cron. Manual refresh is for when you want it sooner (e.g. you just added a new adapter and want to see results).

#### What's NOT on the admin

By design, the admin is read-only over the data:

- You cannot edit shows or venues from the UI.
- You cannot add a venue from the UI — edit `theatres.yaml` and add an adapter in code; the next scrape syncs the catalogue.
- You cannot delete user data because no user data is collected.

Data correction is a deploy: fix the adapter, commit, redeploy, the next scrape (or manual refresh) overwrites the bad rows. This is intentional — the database is treated as derived state.

### Troubleshooting from the admin

**No data on the site / "0 shows"**
- Check scrape status on `/admin`. If the last run is `failed`, click into the GitHub Actions run for the exception.
- Verify `DATABASE_URL` in Vercel project settings is the **pooled** Neon URL (ends in `-pooler.neon.tech`).

**Refresh button does nothing**
- Verify `GITHUB_TOKEN` is set on Vercel and is a fine-grained PAT with `Actions: read & write` on `ruiboom/theatre-scout`.
- Verify `GITHUB_REPO` and `GITHUB_WORKFLOW` env vars match the actual repo and workflow filename.
- Check the response of the POST in the browser network tab — GitHub returns a 422 if the workflow can't be found, 403 if the token is wrong.

**Cannot log in**
- Confirm `ADMIN_PASSWORD` is set on Vercel and matches exactly.
- After updating env vars on Vercel, redeploy — env changes don't apply to running serverless functions until a new build is shipped.

**Stale numbers on the dashboard**
- All `/admin` queries are `force-dynamic` — no caching. If the numbers look wrong, the data really is wrong (check the events table directly or trigger a refresh).

### Operational rhythm

Day-to-day there is nothing to do — cron handles scrapes, data refreshes itself, the dashboard is just for situational awareness.

The admin's job is mainly:

- **Daily** — glance at the dashboard. Is the scrape green? Are visits trending OK?
- **Weekly** — skim top searches. If users keep searching for a term that returns nothing (e.g. a specific show name we don't have), that's signal to add a venue or fix an adapter.
- **When something breaks** — read [MANAGEMENT_PLAYBOOK.md](MANAGEMENT_PLAYBOOK.md) for which platform owns which failure mode.

---

## Part 4 — Reporting issues

The platform has no in-app feedback. If something is wrong, route it through GitHub:

- **Repo:** <https://github.com/ruiboom/theatre-scout> — note this is a **private** repository. You need to be added as a collaborator (Settings → Collaborators on the repo) to file or read issues.
- **Bug in the site** → open a GitHub issue.
- **Wrong show data** → in 99% of cases the venue's own website is wrong or the adapter is parsing it wrong. Open an issue with the venue slug and the show title; the fix is an adapter tweak.
- **Missing venue** → propose it in an issue; we add it to `theatres.yaml` and write an adapter.

---

## See also

- [README.md](README.md) — full technical documentation, architecture, code map.
- [MANAGEMENT_PLAYBOOK.md](MANAGEMENT_PLAYBOOK.md) — Vercel, Neon, Cloudflare ops.
- [SETUP.md](SETUP.md) — local development.
- [DEPLOY.md](DEPLOY.md) — first-time deployment.
- [docs/TOOL_SURFACE.md](docs/TOOL_SURFACE.md) — MCP tool contract (the spec the AI surfaces ride on).
