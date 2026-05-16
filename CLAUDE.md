# Theatre Scout

## What this is

A local Python app that scrapes the websites of 68 London theatres outside the West End and builds a searchable directory of current and upcoming productions — plays, musicals, comedy, dance, opera, family shows. The directory is browseable via a small local web UI; scrapes are triggered manually from the CLI or with a "refresh" button in the UI.

## Status

The local Python scraper described below is built and working. There is
**also** a separate, deployed product under `platform/` — see
[Hosted platform](#hosted-platform). This document covers the local `scout/`
app; when in doubt about it, follow the conventions here. Platform conventions
live in [`platform/README.md`](platform/README.md).

## Hosted platform

`platform/` is an internet-facing system, independent of the local `scout/`
scraper (it has its own Python scrapers, DB, and docs):

- **Website + Internal API** — Next.js on Vercel
  (`https://theatre-scout-zunz.vercel.app`), including public `/privacy` and
  `/terms` pages linked from the site footer.
- **Remote MCP server** — Cloudflare Workers
  (`https://platform-mcp-server.boomclick.workers.dev/mcp`), **OAuth 2.1-protected**
  via `@cloudflare/workers-oauth-provider` so Claude and ChatGPT can add it as
  a connector. Consent is self-issued and anonymous (the listings are public,
  read-only); delegating to a real IdP is the documented upgrade path if
  per-user features are ever needed. `platform/apps/mcp-server/server.json` is
  its MCP Registry manifest; `verify-oauth.sh` checks the OAuth contract.
- **Database** — Neon Postgres. **Scrapers** — `platform/apps/scrapers`, run on
  a GitHub Actions cron.

Detailed docs: [`platform/README.md`](platform/README.md),
[`platform/DEPLOY.md`](platform/DEPLOY.md),
[`platform/apps/mcp-server/README.md`](platform/apps/mcp-server/README.md).

## Tech stack

- **Python 3.11+**
- **HTTP**: `httpx` (sync client by default; async only if a specific adapter needs concurrent fetches)
- **HTML parsing**: `beautifulsoup4` with `lxml`
- **JS-rendering fallback**: `playwright` — only when a site requires it. Plain `httpx` + `bs4` first.
- **DB**: SQLite via stdlib `sqlite3` (file at `data/theatre-scout.db`). No ORM unless complexity demands it.
- **Web UI**: `fastapi` + `jinja2` templates + a tiny bit of vanilla JS. Served with `uvicorn`.
- **CLI**: `typer`
- **Models**: `pydantic` v2
- **Tests**: `pytest`
- **Lint/format**: `ruff` (format + check), `mypy` for type checking
- **Dependency management**: `uv`

## Project layout

```
theatre-scout/
├── CLAUDE.md
├── README.md                    # user-facing, short
├── pyproject.toml
├── theatres.yaml                # master list of venues — single source of truth
├── scout/
│   ├── __init__.py
│   ├── cli.py                   # `scout scrape`, `scout serve`, `scout list`
│   ├── db.py                    # schema + queries (sqlite3)
│   ├── models.py                # Pydantic: Show, Theatre, ScrapeRun
│   ├── scraper.py               # orchestrator: load theatres → dispatch → write
│   ├── http.py                  # shared httpx client, rate limiting, caching
│   ├── adapters/
│   │   ├── __init__.py          # registry: slug → adapter class
│   │   ├── base.py              # BaseAdapter (abstract): fetch() -> list[Show]
│   │   ├── almeida.py
│   │   ├── bridge.py
│   │   └── ...                  # one module per theatre
│   └── web/
│       ├── __init__.py
│       ├── app.py               # FastAPI app
│       ├── templates/
│       └── static/
├── data/
│   └── theatre-scout.db         # SQLite, gitignored
├── .cache/                      # dev HTML cache, gitignored
└── tests/
    ├── fixtures/                # saved HTML samples per theatre
    └── adapters/                # one parse-test file per adapter
```

## How to run

```
uv run scout scrape                  # scrape all theatres
uv run scout scrape --theatre almeida  # scrape one
uv run scout serve                   # local web UI on http://localhost:8000
uv run scout list                    # list known theatres / counts
```

## Data model

**Theatre** (loaded from `theatres.yaml` into the `theatres` table):
- `slug` (PK, e.g. `almeida`)
- `name`
- `area` (e.g. `Islington`)
- `postcode_prefix` (e.g. `N1`)
- `category` (`major` | `mid` | `fringe` | `outer`)
- `url` (homepage)

**Show**:
- `id` (auto)
- `theatre_slug` (FK)
- `title`
- `show_type` (`play`, `musical`, `comedy`, `dance`, `opera`, `family`, `cabaret`, `other`)
- `description` (short summary, may be empty)
- `url` (canonical link to the show page)
- `start_date`, `end_date` (nullable for open-ended runs)
- `price_min`, `price_max` (pence, nullable)
- `image_url` (nullable)
- `first_seen_at`, `last_seen_at` (timestamps)
- `raw_data` (JSON blob for adapter-specific extras)
- Uniqueness: `(theatre_slug, title, start_date)` — re-runs update existing rows.

**ScrapeRun**:
- `id`, `theatre_slug`, `started_at`, `finished_at`, `status` (`success` | `partial` | `failed`), `shows_found`, `error` (nullable text)

## Scraping conventions

- **Rate limit**: max 1 request/second per host. Implemented in `scout/http.py` as a per-host token bucket.
- **User-Agent**: `TheatreScout/0.1 (+local research bot)`.
- **robots.txt**: honor it. Skip disallowed paths and log a warning.
- **HTML cache**: in dev, cache responses to `.cache/` for 1 hour to avoid hammering sites while iterating on a parser.
- **Prefer structured data**: if a page exposes `application/ld+json` with schema.org `Event` or `TheaterEvent`, parse that first. Fall back to HTML scraping.
- **Failure isolation**: one adapter raising must not crash the run. The orchestrator records a `failed` ScrapeRun for that theatre and moves on.
- **Be polite**: no parallel hammering of a single domain; concurrency across distinct domains is fine.
- **No login walls, no scraping behind paywalls.**

## Theatre categories

Full list lives in [`theatres.yaml`](theatres.yaml). Counts:

- `major` — Major producing houses & flagship Off-West End: **18 theatres** (Almeida, Bridge, Bush, Donmar, Hampstead, Kiln, Lyric Hammersmith, Menier Chocolate Factory, National, Old Vic, Open Air, Orange Tree, Royal Court, Sadler's Wells, Shakespeare's Globe, Soho, Theatre Royal Stratford East, Young Vic)
- `mid` — Mid-sized & specialist venues: **19 theatres** (Arcola, Barbican, Brixton House, Charing Cross, Coronet, Gate, Hackney Empire, Marylebone, New Diorama, Park, Pleasance, Riverside Studios, Roundhouse, Seven Dials Playhouse, The Other Palace, The Yard, Underbelly Boulevard, Unicorn, Wilton's Music Hall)
- `fringe` — Fringe & pub theatres: **19 theatres** (Camden People's, Cockpit, Drayton Arms, Etcetera, Finborough, Hen & Chickens, Jermyn Street, King's Head, Old Red Lion, Omnibus, Southwark Playhouse, Tabard, Tara, The Vaults, Tower, Union, Upstairs at the Gatehouse, Waterloo East, White Bear)
- `outer` — Outer London receiving houses & large-scale venues: **12 theatres** (Alexandra Palace, Bloomsbury, Churchill, Eventim Apollo, Greenwich, New Wimbledon, Polka, Queen's Hornchurch, Richmond, Rose Kingston, Troubadour Canary Wharf, Troubadour Wembley Park)

## Adding a new theatre adapter

1. Add the venue to `theatres.yaml` with a unique kebab-case `slug`.
2. Save a representative HTML sample to `tests/fixtures/<slug>.html` (use `curl -A "TheatreScout/0.1 (+local research bot)" <url>`).
3. Create `scout/adapters/<slug>.py` implementing `BaseAdapter.fetch() -> list[Show]`.
4. Register it in `scout/adapters/__init__.py` (slug → class).
5. Write `tests/adapters/test_<slug>.py` that loads the fixture and asserts the parsed `Show` objects.
6. Run `uv run pytest tests/adapters/test_<slug>.py` and `uv run scout scrape --theatre <slug>` to verify end-to-end.

## Secrets & environment

- **Never commit env files.** `.env*` is gitignored except `.env.example` (the
  template). A real `.env.production` was once committed and had to be purged
  from git history — do not repeat that.
- Production credentials live only in their platform's secret store. The Neon
  connection string is **Vercel env `DATABASE_URL`** (pooled, used by the
  website/API) and **GitHub Actions secret `NEON_DATABASE_URL`** (direct, used
  by the scraper cron — matches `.github/workflows/scrape.yml`). Rotating the
  Neon password means updating both, then redeploying Vercel.
- The hosted MCP server's inbound auth is OAuth (no shared secret); provider
  state lives in the Cloudflare `OAUTH_KV` namespace.
- `gitleaks` runs against full history; config at repo root
  [`.gitleaks.toml`](.gitleaks.toml). `tests/fixtures/` is allowlisted — those
  scraped HTML samples embed the *theatre sites'* own public front-end keys
  (Google Maps, Algolia, analytics), not ours.

## Code conventions

- `ruff format` and `ruff check` pass before commit.
- `mypy scout/` is clean.
- Small, focused commits. One adapter per commit when adding multiple.
- No unused imports, no commented-out code, no `TODO` without an owner.
- Comments explain *why*, not *what*.
- Adapters are pure functions of `(html, url) → list[Show]` where possible — keeps them trivially testable.
