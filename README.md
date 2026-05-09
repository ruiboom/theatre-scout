# Theatre Scout

A local Python app that scrapes 68 London theatres outside the West End and serves a searchable directory of current and upcoming shows — plays, musicals, comedy, dance, opera, family shows. Browse it at `http://localhost:8000` after a one-line scrape.

**Current scope:** 68 registered venues, 55 returning shows on the last run, ~1,000 upcoming productions in the database.

---

## Table of contents

- [What it is](#what-it-is)
- [System requirements](#system-requirements)
- [First-time setup](#first-time-setup)
- [Day-to-day commands](#day-to-day-commands)
- [User guide (web UI)](#user-guide-web-ui)
- [CLI reference](#cli-reference)
- [Architecture](#architecture)
- [Data model](#data-model)
- [How scraping works](#how-scraping-works)
- [Adding a new venue](#adding-a-new-venue)
- [Fixing a broken adapter](#fixing-a-broken-adapter)
- [Development](#development)
- [Known limitations](#known-limitations)
- [Further reading](#further-reading)

---

## What it is

A self-contained directory of London Off-West-End theatre, refreshed on demand. The app:

1. **Scrapes** each venue's "what's on" page, politely (1 req/sec/host, robots.txt-aware, declared User-Agent).
2. **Parses** the listings — preferring schema.org JSON-LD, falling back to per-venue CSS adapters, escalating to a stealth headless browser only where the site is JavaScript-rendered.
3. **Stores** results in a local SQLite database (`data/theatre-scout.db`).
4. **Serves** them via a small FastAPI/Jinja web UI with rails and list views, search, and category/show-type filters.

There is no signup, no analytics, no external services. Everything runs on your laptop.

---

## System requirements

- **macOS or Linux** (Windows untested; should work via WSL).
- **Python 3.11+** — `pyproject.toml` declares `>=3.11`.
- **[`uv`](https://docs.astral.sh/uv/)** for dependency management. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` if you don't have it.
- **~500 MB free disk** for the headless browser (Chromium via Patchright). Required only by 7 venues whose listings are JavaScript-rendered; you can skip the browser install if you're happy to leave those venues blank.
- **Internet access** when scraping. The cached DB works offline once populated.

---

## First-time setup

```bash
# 1. Clone (or you're already here)
cd theatre-scout

# 2. Install Python deps into a local .venv
uv sync

# 3. (Optional but recommended) install the browser binaries used by the
#    stealth fetch path. ~500 MB; one-off cost.
uv run scrapling install --force

# 4. Pull every venue's listings into the local DB. ~2 min for plain venues,
#    +1-2 min for the JS-rendered ones if you ran step 3.
uv run scout scrape

# 5. Serve the web UI
uv run scout serve
# → open http://localhost:8000
```

That's it. The app is now usable. Re-run step 4 whenever you want fresh data, or hit the **Refresh** button in the top-right of the web UI.

---

## Day-to-day commands

```bash
# Refresh the DB and serve — the common loop
uv run scout scrape                                  # ~2-5 min
uv run scout serve                                   # http://localhost:8000

# Refresh with descriptions and prices from detail pages (slower)
uv run scout scrape --enrich --replace --workers 8   # ~3-6 min

# One specific venue (great while iterating on an adapter)
uv run scout scrape --theatre soho-theatre --replace
uv run scout scrape --theatre union --enrich --replace --workers 4

# List all known venues + slug → adapter mapping
uv run scout list
```

The `--replace` flag wipes existing rows for any venue that successfully re-scrapes (preserving rows for venues whose scrape failed). Without `--replace` you get an upsert-by-`(theatre_slug, title, start_date)`.

The `--enrich` flag fetches each show's detail page after the listing scrape, pulling descriptions, hero images, and (where the venue exposes them) prices.

`--workers N` parallelises the enrichment step across hosts. Per-host rate limiting still serialises within a single host, so two shows at the same venue still run one-after-the-other; venues run in parallel. Stealth fetches additionally pin to a single browser-owner thread.

---

## User guide (web UI)

The UI is intentionally small. Three pages:

### `/` — venue index

Theatres grouped into four categories (`major`, `mid`, `fringe`, `outer`) with show counts. Clicking a venue takes you to its detail page. The top-right shows when the database was last refreshed and offers a Refresh button.

### `/theatres/<slug>` — venue detail

The venue's full programme (every show currently in the DB), with hero info: name, area, postcode, link to the box office, and a small map (when geocoded). Below: a list of shows with title, dates, image, type tag, price (where known), and a truncated description.

### `/shows` — every show

The flat catalogue. Two view chips at the top:

- **Rails** (default): shows grouped into category rails (Major / Mid / Fringe / Outer), each with a horizontal-scroll preview and a "View all" link.
- **List**: the full table-style list, sortable by Opening date / Closing date / Title / Venue.

Filters above the list: search box, category checkboxes, show-type filter (play / musical / comedy / dance / opera / family / cabaret / other). All filters compose into the URL so links are shareable.

### Per-row interactions

In every list/card, the row is broken into separately clickable elements rather than one giant link:

- **Title** — clicks through to the venue's external show page (new tab). Hovering shows the full description as a native browser tooltip.
- **Venue name** — links internally to that venue's detail page.
- Image, dates, idx, tag — non-interactive.

### Refresh button

`POST /refresh` triggers a full `--enrich --replace --workers` scrape in the background. The button shows progress and you can navigate while it runs; the page auto-updates when done.

---

## CLI reference

```text
scout scrape [--theatre <slug>] [--enrich] [--replace] [--workers N]
    Scrape venue listings into the local DB.
    --theatre <slug>   Only this venue (default: all).
    --enrich           After listings, fetch each show's detail page for
                       description, image and (where supported) price.
    --replace          Wipe existing rows for each venue before insert
                       (only on successful scrape).
    --workers N        Parallel workers for the enrich step (default: 1).

scout serve [--port N] [--host HOST]
    Start the FastAPI/Jinja web UI. Default: 127.0.0.1:8000.

scout list
    Print every registered venue (slug, name, category, area).

scout --help
    Full help including hidden flags.
```

---

## Architecture

```
theatre-scout/
├── theatres.yaml                 # 68 venues — single source of truth
├── theatre-coords.yaml           # optional geocoded lat/lon for the venue map
├── pyproject.toml                # uv-managed dependencies
├── README.md                     # this file
├── CLAUDE.md                     # canonical conventions / AI-assistant brief
├── BUILD.md                      # historical milestone log
│
├── scout/
│   ├── cli.py                    # Typer entrypoint: scrape / serve / list
│   ├── db.py                     # SQLite schema + queries (no ORM)
│   ├── http.py                   # rate-limited, robots-aware client + stealth
│   ├── models.py                 # Pydantic v2: Show, Theatre, ScrapeRun
│   ├── classify.py               # heuristic show-type classifier
│   ├── enrich.py                 # generic detail-page extractors
│   ├── scraper.py                # orchestration (run_one / run_all)
│   ├── text.py                   # text-cleaning helpers
│   ├── theatres.py               # YAML loader for theatres.yaml
│   │
│   ├── adapters/                 # one module per scraping strategy
│   │   ├── base.py               # BaseAdapter (abstract: parse + enrich)
│   │   ├── registry.py           # @register decorator → slug map
│   │   ├── _generic.py           # GenericAdapter (JSON-LD, then card CSS)
│   │   ├── _jsonld.py            # schema.org Event extractor
│   │   ├── _html.py              # date helpers
│   │   ├── _ticketsolve.py       # shared Ticketsolve helper
│   │   ├── bulk.py               # 58 thin GenericAdapter subclasses
│   │   ├── almeida.py            # bespoke per-venue adapters ↓
│   │   ├── bloomsbury.py
│   │   ├── donmar_warehouse.py
│   │   ├── park_theatre.py
│   │   ├── pleasance.py
│   │   ├── soho_theatre.py
│   │   ├── union.py
│   │   ├── upstairs_at_the_gatehouse.py
│   │   ├── vaults.py
│   │   └── waterloo_east.py
│   │
│   └── web/
│       ├── app.py                # FastAPI routes
│       ├── templates/            # Jinja: base / index / shows / theatre
│       └── static/               # CSS + tiny JS
│
├── data/
│   └── theatre-scout.db          # SQLite, gitignored
├── .cache/                       # dev HTML cache, gitignored
└── tests/
    ├── adapters/                 # one test file per bespoke adapter
    ├── fixtures/                 # saved HTML samples
    └── test_*.py                 # framework tests (db, http, web, etc.)
```

### Request flow

```
CLI (scout scrape)
    ↓
scraper.run_all(client, conn)
    ↓                            ↓                        ↓
Phase 1 (serial)             Phase 2 (parallel)        Phase 3 (serial)
listings per adapter   →     enrichment per show    →  DB writes per venue
```

Phase 1 is serial because some venues share a stealth browser session. Phase 2 fans out across hosts but the per-host rate limit serialises within each host, and stealth fetches all funnel through one dedicated browser-owner thread (Patchright greenlets bind to whatever thread opens the session, so we can't share across worker threads). Phase 3 is serial against SQLite.

### HTTP client (`scout/http.py`)

- `Client.get(url, *, stealth=False)` — plain or stealth.
- Per-host token bucket rate limiter (`min_interval=1.0s`).
- robots.txt fetched once per host and cached in-process.
- Plain path uses Scrapling's `FetcherSession` (curl_cffi + Chrome TLS impersonation).
- Stealth path uses `StealthySession` (Patchright headless browser). All stealth calls run on a dedicated single-thread executor so the session stays bound to one greenlet thread.

---

## Data model

### Theatre (`theatres` table, loaded from `theatres.yaml`)

| Column            | Type | Notes                                   |
|-------------------|------|-----------------------------------------|
| `slug`            | PK   | kebab-case, e.g. `donmar-warehouse`     |
| `name`            | text | Display name                            |
| `area`            | text | e.g. `Islington`                        |
| `postcode_prefix` | text | e.g. `N1`                               |
| `category`        | text | `major` / `mid` / `fringe` / `outer`    |
| `url`             | text | Venue homepage                          |

### Show (`shows` table)

| Column          | Type     | Notes                                                                  |
|-----------------|----------|------------------------------------------------------------------------|
| `id`            | PK auto  |                                                                        |
| `theatre_slug`  | FK       | references `theatres.slug`                                             |
| `title`         | text     |                                                                        |
| `show_type`     | text     | `play`/`musical`/`comedy`/`dance`/`opera`/`family`/`cabaret`/`other`   |
| `description`   | text     | may be empty                                                           |
| `url`           | text     | canonical link to the show page                                        |
| `start_date`    | date?    | nullable for open-ended runs                                           |
| `end_date`      | date?    |                                                                        |
| `price_min`     | int?     | pence                                                                  |
| `price_max`     | int?     | pence                                                                  |
| `image_url`     | text?    |                                                                        |
| `raw`           | json     | adapter-specific extras                                                |
| `first_seen_at` | datetime | UTC ISO                                                                |
| `last_seen_at`  | datetime | UTC ISO                                                                |

Uniqueness: `(theatre_slug, title, COALESCE(start_date, ''))`. Re-runs upsert by that key. With `--replace`, prior `first_seen_at` is preserved by URL match so the "new shows" query keeps working when a bespoke adapter changes title shape.

### ScrapeRun (`scrape_runs` table)

`id`, `theatre_slug`, `started_at`, `finished_at`, `status` (`success`/`partial`/`failed`), `shows_found`, `error`.

### Categories (in `theatres.yaml`)

- `major` (18) — Almeida, Bridge, Bush, Donmar, Hampstead, Kiln, Lyric Hammersmith, Menier, National, Old Vic, Open Air, Orange Tree, Royal Court, Sadler's Wells, Shakespeare's Globe, Soho, Theatre Royal Stratford East, Young Vic
- `mid` (19) — Arcola, Barbican, Brixton House, Charing Cross, Coronet, Gate, Hackney Empire, Marylebone, New Diorama, Park, Pleasance, Riverside Studios, Roundhouse, Seven Dials, The Other Palace, The Yard, Underbelly Boulevard, Unicorn, Wilton's
- `fringe` (19) — Camden People's, Cockpit, Drayton Arms, Etcetera, Finborough, Hen & Chickens, Jermyn Street, King's Head, Old Red Lion, Omnibus, Southwark Playhouse, Tabard, Tara, The Vaults, Tower, Union, Upstairs at the Gatehouse, Waterloo East, White Bear
- `outer` (12) — Alexandra Palace, Bloomsbury, Churchill, Eventim Apollo, Greenwich, New Wimbledon, Polka, Queen's Hornchurch, Richmond, Rose Kingston, Troubadour Canary Wharf, Troubadour Wembley Park

---

## How scraping works

### Two adapter shapes

**Generic adapter** (~50 venues): one line in `scout/adapters/bulk.py` of the form `(slug, listings_url, css_selector)`. The `GenericAdapter` tries JSON-LD first, then walks elements matching `css_selector` and pulls title/link/image/dates with default heuristics. Good for 70 % of venues.

**Bespoke adapter** (currently 10): a per-venue file in `scout/adapters/<slug>.py` subclassing `BaseAdapter`. Used when the page is JS-rendered, has badly-named anchors that break the generic title heuristic, paginates, or needs custom date parsing. Current bespoke set:

- `almeida.py` — pilot adapter, `.c-event-card__wrapper` cards.
- `bloomsbury.py` — JS-rendered listing at `/events`; UK `dd/mm/yyyy` dates.
- `donmar_warehouse.py` — semantic `c-media__event` cards with ISO `<time>` elements.
- `park_theatre.py`, `pleasance.py` — bespoke listing parsers (the latter filters to London-only shows).
- `soho_theatre.py` — paginates via `/dean-street/page/N/`; per-card extraction with 2-digit-year date parsing and `From £N` price extraction.
- `union.py` — listing has "Read more" buttons; detail pages expose structured prices.
- `upstairs_at_the_gatehouse.py` / `waterloo_east.py` — JS-rendered Ticketsolve subdomain (shared `_ticketsolve.py` helper).
- `vaults.py` — listing redirects to a single Lineup event-detail page; dates from a calendar widget.

### Per-adapter `enrich()` hook

Adapters can override `enrich(html, base_url) -> dict[str, Any]` to extract richer fields from a show's detail page. The default calls the generic `extract_description` + `extract_image` from `scout/enrich.py`. Bespoke overrides exist for:

- **Union** — pulls description from `#show > p`, prices from `<h2>Tickets</h2>` `<ul>`.
- **Ticketsolve venues** — picks the longest substantive paragraph in `<main>` (the first ≥60 char p is usually title/credits).

The orchestrator (`scout/scraper.py::_enrich`) merges with these rules: description only fills if currently empty, image always overwrites (detail-page hero usually beats listing thumb), prices only fill if currently None. Detail-page fetches inherit the adapter's `requires_js` flag.

### Scraping conventions

- **Rate limit**: max 1 request/second per host (`scout/http.py::RateLimiter`).
- **User-Agent**: `TheatreScout/0.1 (+local research bot)`.
- **robots.txt**: honoured. Disallowed paths are skipped with a warning.
- **HTML cache**: in dev, responses cached to `.cache/` for 1 hour.
- **Failure isolation**: one adapter raising never crashes the run — the orchestrator records a failed `ScrapeRun` for that venue and moves on.
- **No login walls, no scraping behind paywalls.**

---

## Adding a new venue

1. **Add to `theatres.yaml`** with a unique kebab-case `slug`, name, area, postcode prefix, category, and homepage URL.
2. **Save a representative HTML sample** to `tests/fixtures/<slug>.html`:
   ```bash
   curl -A "TheatreScout/0.1 (+local research bot)" \
       https://example.com/whats-on > tests/fixtures/<slug>.html
   ```
   For JS-rendered sites use a stealth fetch via Python:
   ```python
   from scout.http import Client
   c = Client(); print(c.get("https://...", stealth=True).text); c.close()
   ```
3. **Try the generic adapter first.** Add an entry to `scout/adapters/bulk.py`:
   ```python
   ("my-venue", "https://example.com/whats-on", 'a[href*="/event/"]'),
   ```
   Then `uv run scout scrape --theatre my-venue --replace` and inspect the DB.
4. **If the generic adapter falls short** (button-text titles, missing fields, pagination, JS-rendered), write a bespoke adapter:
   - Create `scout/adapters/my_venue.py` subclassing `BaseAdapter`. Use `pleasance.py` or `donmar_warehouse.py` as templates.
   - Set `requires_js = True` if the page needs the stealth path.
   - Optionally override `enrich()` for detail-page extraction.
   - Write `tests/adapters/test_my_venue.py` loading the fixture and asserting `Show` fields.
   - Remove the now-redundant entry from `bulk.py`.
5. **Verify**:
   ```bash
   uv run pytest tests/adapters/test_my_venue.py
   uv run scout scrape --theatre my-venue --replace
   ```
6. **Commit** in a focused commit per project convention (one adapter per commit).

See `CLAUDE.md` for the full coding conventions.

---

## Fixing a broken adapter

When a venue redesigns their site or starts returning button-text titles like "Book now":

```bash
# 1. Re-capture the live page
curl -A "TheatreScout/0.1 (+local research bot)" \
    https://example.com/whats-on > tests/fixtures/<slug>.html

# 2. Run the existing adapter test against the new fixture — it'll fail
uv run pytest tests/adapters/test_<slug>.py -v

# 3. Inspect the new HTML, update the adapter selectors, re-run
# 4. Live-verify
uv run scout scrape --theatre <slug> --replace
```

If the generic adapter starts returning bad titles, promote the venue to a bespoke adapter as above.

---

## Development

```bash
uv run pytest                      # all tests (~3 sec)
uv run pytest tests/adapters/      # adapter tests only (very fast — fixture-based)
uv run ruff format .               # format
uv run ruff check .                # lint
uv run mypy scout                  # type check
```

### Conventions

- `ruff format` and `ruff check` pass before commit.
- `mypy scout/` is clean.
- Small, focused commits. **One adapter per commit** when adding multiple.
- No unused imports, no commented-out code, no `TODO` without an owner.
- Comments explain *why*, not *what*.
- Adapters are pure functions of `(html, url) → list[Show]` where possible — keeps them trivially fixture-testable.
- Lower layers (`db.py`, `models.py`, `scraper.py`) must not import `typer` / `fastapi`. Enforced by `tests/test_layering.py`.

### Test fixtures

Each bespoke adapter has at least one HTML fixture under `tests/fixtures/<slug>.html` (and detail-page fixtures under `tests/fixtures/<slug>_show_<scenario>.html` where enrichment is tested). Fixtures are committed to git so adapter tests run offline and fail fast when a site changes.

---

## Known limitations

- **Some JS venues still don't render** — Yard, Seven Dials Playhouse use the generic adapter via the stealth path. Hen & Chickens, Tabard hit DNS/SSL issues in past scrapes; left as plain-HTTP entries.
- **Free-show pricing** — `_parse_price` skips £0 (treats them as access/comp tickets). A genuinely free show would currently come back with `price_min = NULL`.
- **2-digit-year dates** — Soho's `Sat 9 May 26` parser assumes 20YY. Will misread a date written as `26` if you scrape pre-2000 archive content (won't happen in practice).
- **Stealth concurrency** — all stealth fetches serialise behind one browser thread. Parallel speed-up only applies to the plain-HTTP venues.
- **Description quality varies** — venues without a synopsis paragraph leave `description` empty even after `--enrich`. The UI handles this gracefully.

---

## Further reading

- **[CLAUDE.md](CLAUDE.md)** — canonical project conventions and AI-assistant brief. Read this if you're building on top.
- **[BUILD.md](BUILD.md)** — milestone-by-milestone history of how the app was built.
- **[QUESTION_LOG.md](QUESTION_LOG.md)** — autonomous decisions taken during the build.
- **[RUN.md](RUN.md)** — operational runbook (covered by this README's Day-to-day commands section).
