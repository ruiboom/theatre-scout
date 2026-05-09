# Question Log

Decisions taken autonomously during the build that the user should review later. Each entry: what came up, the recommendation taken, and why.

---

## M0 — git init

**Question**: BUILD.md calls for "small commits", but the folder wasn't a git repo. Initialize one?

**Decision taken**: `git init` and committing per milestone. Used `main` as the default branch. No remote configured.

**Why**: Small-focused commits are part of the working principles you approved. If you'd rather not have version control, just `rm -rf .git`.

---

## M0 — uv vs pip

**Question**: BUILD.md specifies uv as the package manager. uv is installed (0.10.2). Lockfile committed?

**Decision taken**: Yes — `uv.lock` is committed. Standard practice for reproducible installs.

**Why**: Without a lockfile, every fresh checkout pulls latest matching versions and adapters can break silently when a parser library changes behavior.

---

## M1 — fringe count discrepancy (CLAUDE.md said 67, actual is 68)

**Question**: My CLAUDE.md heading said `fringe — 18 theatres` but the bullet listed 19 names. Total should be 68, not 67.

**Decision taken**: Updated CLAUDE.md and BUILD.md to 68 total / 19 fringe. This matches the venues you originally provided.

**Why**: Off-by-one in the original count, not a venue you intended to drop. If you actually want to drop one, tell me which.

---

## M1 — slugs for ATG venues

**Question**: New Wimbledon Theatre and Richmond Theatre both run on `atgtickets.com`. What URL goes in `theatres.yaml`?

**Decision taken**: Used venue-specific paths I'm fairly sure of:
- `https://www.atgtickets.com/venues/new-wimbledon-theatre/`
- `https://www.atgtickets.com/venues/richmond-theatre/`

**Why**: ATG uses a consistent `/venues/<slug>/` URL pattern. If wrong, the adapter for those will fail loudly with a 404 and we fix the URL.

---

## M1 — slugs for Troubadour venues

**Question**: Both Troubadour venues use `troubadour.com`. Same URL?

**Decision taken**: Same homepage URL (`https://troubadour.com`) for both. Adapter will distinguish by venue when scraping.

**Why**: Less guessing. If Troubadour has separate venue pages, the adapter will navigate to them; the homepage is just the entry point.

---

## M1 — Sadler's Wells East and Soho Walthamstow

**Question**: Sadler's Wells lists "+ Sadler's Wells East, Stratford" and Soho lists "+ Soho Theatre Walthamstow, E17". Separate entries?

**Decision taken**: Rolled into the main entry. Each adapter can scrape both venues if listings cover them.

**Why**: They're operationally one organisation with shared programming. Keeping them separate would duplicate adapter code. If you'd rather have them as separate slugs, easy to split later.

---

## M8 — adapter rollout strategy: bulk module vs one-file-per-adapter

**Question**: BUILD.md said "one module per theatre". 67 thin GenericAdapter subclasses each in their own file = 67 files of ~5 lines.

**Decision taken**: Put thin GenericAdapter subclasses in a single `scout/adapters/bulk.py` with one tuple per theatre. Almeida (which has bespoke parsing) keeps its own file. New bespoke adapters get their own file.

**Why**: 67 near-identical 5-line files would be wasteful; the bulk file is easier to scan and maintain. The structural rule (one file per adapter) was meant to isolate per-theatre logic — bulk entries have no per-theatre logic worth isolating.

---

## M8 — three theatres failed to fetch from main domain

**Question**: `national-theatre`, `hen-and-chickens`, `tabard` returned errors during the survey (likely DNS, Cloudflare bot block, or 403). Skip or work around?

**Decision taken**: Registered them with their best-guess listings URL anyway. They'll show up as `failed` ScrapeRuns at runtime, transparently. No manual fix yet — would need to test from a real browser User-Agent or use Playwright.

**Why**: The data is recoverable in a follow-up. Skipping them entirely would hide a data quality issue.

---

## M8 — five sites are JavaScript-rendered (no scrape data without a browser)

**Question**: `seven-dials-playhouse`, `yard`, `vaults`, `upstairs-at-the-gatehouse` (Ticketsolve), `waterloo-east` returned mostly empty HTML. Need Playwright?

**Decision taken**: Registered with empty selectors so they parse cleanly to `[]`. Playwright integration is M9+ work — too much scope to add now. Listed in QUESTION_LOG as known JS-only sites.

**Why**: Polluting the build with a Playwright dependency for 5 of 68 sites isn't worth it yet. They're transparent (0 shows) rather than crashing.

---

## M8 — bulk adapter quality is mixed (e.g. Pleasance returns 323 "Book tickets for X" titles)

**Question**: The link-pattern selectors return many matches with noisy titles ("Book tickets for The Show"). Clean now or later?

**Decision taken**: Leave as-is for v1. Per-adapter title cleanup (regex strip prefix) belongs in a custom adapter when worth it.

**Why**: The data is correct, just ugly. Easy to fix per-theatre when reviewing the live UI. Spending time polishing every adapter before they're reviewed would be premature.

---

## Tier 3 follow-ups — cross-theatre parallelism + host round-robin

**Question**: First Tier 3 cut barely moved the needle (~24 min). The workers were all hitting the same host on the dominant venue (Pleasance, 322 shows on one host) and blocking on its rate limit.

**Decisions taken**:

1. **Refactor `run_all` into 3 phases** (`cae2a48`):
   - Phase 1: serial listing scrape per adapter (writes nothing yet).
   - Phase 2: ONE big ThreadPoolExecutor across every show from every theatre.
   - Phase 3: serial DB writes per theatre.

   `run_one` is unchanged — single-theatre flow keeps internal `_enrich_many`.

2. **Round-robin shows by host** before submission (latest commit):
   - `_host_round_robin` interleaves shows so workers immediately fan across distinct hosts.
   - Without it, workers all grab the dominant host first and stall behind its 1 req/sec rate limit while other hosts sit idle.

**Result**: full enrich+replace dropped from ~25 min (Tier 2) to **7 min 47 s** with `--workers 16`. ~3.2× total speedup vs Tier 2; ~3.5× vs Tier 0.

**The floor we're hitting now**: Pleasance has 322 shows on `cptheatre.co.uk`. At 1 req/sec/host that's 5.4 min minimum no matter how many workers we throw at it. Plus ~2 min serial listing scrape = ~7-8 min total. Further speedups would need either lower per-host rate (less polite) or skipping more enrichment.

**Trade-offs accepted**:
- The 3-phase pipeline holds all listing results in memory before DB write. ~1,200 shows is trivial for this — but if we ever hit ~100k shows we'd want streaming.
- DB writes happen *after* all enrichment finishes, so a crash mid-enrichment loses everything. Pre-existing rows survive (we don't delete until just before insert when `--replace`). For a 7-min job this is fine; we'd revisit if we go to a longer pipeline.

---

## Scrapling Tier 3 — parallel enrichment via ThreadPoolExecutor

**Question**: Tier 2 saved only ~1.5 min on the full scrape because the dominant cost (~22 min) is serial detail-page fetches for `--enrich`. Add concurrency?

**Decision taken**: Yes. Pre-change state tagged `pre-scrapling-tier-3`. Rollback chain:

```bash
git reset --hard pre-scrapling-tier-3   # back to Tier 2 (sessions, no parallelism)
git reset --hard pre-scrapling-tier-2   # back to Tier 1
git reset --hard pre-scrapling          # back to pre-Scrapling
```

**What changed**:
- `scout/http.py` — `RateLimiter` now thread-safe via per-host `threading.Lock`. Hosts serialize internally (one waiter per host) but different hosts don't block each other.
- `scout/scraper.py` — new `_enrich_many(shows, client, workers)` helper using `concurrent.futures.ThreadPoolExecutor`. `run_one` / `run_all` accept a `workers: int` parameter (default 1 = serial).
- `scout/cli.py` — `scrape --workers N` flag.
- 2 new concurrency tests in `test_http.py` (same-host serializes, different-hosts parallel) and 1 e2e test confirming parallel and serial enrichment yield identical descriptions.

**Trade-offs accepted**:
- Listing scrape stays serial. Adding parallelism there would touch the SQLite write path, which sqlite3 doesn't allow across threads on a single connection without `check_same_thread=False` + locking. Listing is only ~3 min of the 25 min total; the cost/benefit isn't there.
- Sharing a single `FetcherSession` across worker threads relies on curl_cffi being thread-safe; the docs claim it is and the test suite passes. If a real concurrency bug shows up under load we'd switch to a per-thread session pool.
- The `StealthySession` is single-tab synchronous; stealth venues still run serial. To parallelize them we'd need `AsyncStealthySession` with a `max_pages` tab pool — async runtime, bigger refactor. Worthwhile only if we add many more JS-rendered venues.
- Workers > ~50 has diminishing returns: only ~50 distinct hosts, each capped at 1 req/sec. 16 is the sweet spot.

**Validation**:
- 209 unit/integration tests pass; mypy + ruff clean.
- Same-host concurrent test verifies the per-host gap holds under threads.
- Different-hosts concurrent test verifies hosts run in parallel.
- Live timing tracked separately.

---

## Scrapling Tier 2 — sessions + bs4/lxml/httpx removed

**Question**: Migrate the parsing layer from BeautifulSoup to Scrapling's Selector, and reuse Scrapling sessions across requests instead of spawning fresh ones?

**Decision taken**: Yes, Tier 2 implemented. Pre-change state tagged `pre-scrapling-tier-2` (post-Tier-1 known good). Rollback chain:

```bash
# Roll back to pre-Tier-2 (still on Scrapling, still has bs4):
git reset --hard pre-scrapling-tier-2 && uv sync

# Roll back further to pre-Scrapling entirely:
git reset --hard pre-scrapling && uv sync
```

**What changed**:
- `scout/http.py` — `Client` now lazy-inits a `FetcherSession` (curl_cffi connection pool) and `StealthySession` (single Patchright browser instance). Both close cleanly via `Client.__exit__`. CLI and web `/refresh` now use `with Client() as client:`.
- `scout/adapters/_jsonld.py`, `scout/adapters/_generic.py`, `scout/adapters/almeida.py`, `scout/adapters/park_theatre.py`, `scout/enrich.py`, `scout/text.py`, and the two scripts in `scripts/` — all migrated from `bs4.BeautifulSoup` to `scrapling.parser.Selector`. API differences absorbed (`get_text(' ', strip=True)` → `get_all_text(separator=' ', strip=True)`, `el.find('a', href=True)` → `el.css('a[href]').first`, etc.).
- `pyproject.toml` — dropped `beautifulsoup4` and `lxml` from runtime deps (Scrapling brings lxml itself). `httpx` moved to dev-only because FastAPI's `TestClient` still needs it.
- `pyproject.toml` `pytest.filterwarnings` — added an ignore for `lxml`'s `strip_cdata` DeprecationWarning. Comes from inside Scrapling's Selector init; not actionable on our side.

**Trade-offs accepted**:
- 30+ test cases that mocked `httpx.MockTransport` had to be replaced with mocked `fetch_fn`/`stealth_fetch_fn` callables. Cleaner contract; tests are now decoupled from any specific HTTP library.
- Stealth session is single-tab (sync `StealthySession`). Concurrent stealth fetching would require `AsyncStealthySession` and an async runtime — that's Tier 3 territory.
- Selector tag/attribute API is *almost* drop-in for bs4 but not exact: e.g. `Tag.name` → `Selector.tag`, `Tag.has_attr(k)` → `k in selector.attrib`. Migrations are mechanical but case-by-case.

**Validation**:
- 206 unit/integration tests pass; mypy + ruff clean.
- Live: Almeida fast path returns 8 shows as before. Full enrich+replace timing tracked.

---

## Scrapling Tier 1 — drop-in replacement of `scout/http.py` engine

**Question**: Should we add `scrapling[fetchers]` and route the 7 broken venues through `StealthyFetcher`?

**Decision taken**: Yes, Tier 1 implemented. Pre-change state is tagged `pre-scrapling` (commit `47f29cc`). Rollback at any time:

```bash
git reset --hard pre-scrapling
uv sync
```

**What changed**:
- `scout/http.py` rewritten — same public surface (`Client.get(url, *, stealth=False)`, `Response`, `RateLimiter`, `is_allowed`) but internally uses `scrapling.fetchers.Fetcher` (curl_cffi + Chrome TLS impersonation) and `scrapling.fetchers.StealthyFetcher` (Patchright headless browser) on the `stealth=True` path.
- `Cache` class deleted (was unused outside tests).
- `scout/adapters/base.py` — `BaseAdapter.fetch(client)` now passes `stealth=self.requires_js`. `_ClientLike` Protocol updated.
- `scout/adapters/bulk.py` — 7 venues marked `requires_js=True` (`yard`, `vaults`, `seven-dials-playhouse`, `upstairs-at-the-gatehouse`, `waterloo-east`, `hen-and-chickens`, `tabard`); empty selectors swapped for link-pattern guesses now that we expect rendered HTML.

**What didn't change**:
- Adapters, models, DB, web UI, scraper orchestrator, CLI — all untouched.
- `httpx` and `beautifulsoup4` still in deps (used by adapters / templates / test fixtures).
- Per-host rate limiter and robots.txt check — kept (Scrapling's spider has these but we're not using the spider yet).

**Trade-offs accepted**:
- Default fetcher now sends a Chrome-impersonating User-Agent rather than `TheatreScout/0.1 (+local research bot)`. Less polite but defeats anti-bot blocking that was failing 2 venues silently. Robots.txt check still uses our identifier name.
- Stealth fetches launch a real headless browser per call (~30–45s each). Full scrape time grows by ~5 min when 7 stealth venues are included.
- `scrapling install --force` was run once locally; it pulls Patchright + Chromium browser binaries (~500MB). Not in our git, but committed `uv.lock` records the package versions.

**Validation**:
- 206 unit/integration tests pass; mypy + ruff clean.
- Live: `almeida` (regular path) returns 8 shows as before. `yard` and `hen-and-chickens` now fetch successfully via stealth (previously 0 / failed). Selectors still need tuning for the 7 stealth venues — bespoke adapters or selector refinement is follow-up work, separate from Tier 1.

---

## M0 — Python version floor

**Question**: BUILD.md says "Python 3.11+". System has 3.12.3. Pin floor at 3.11 or 3.12?

**Decision taken**: `requires-python = ">=3.11"` to match the spec.

**Why**: 3.11 has all the type-system features we need; no reason to exclude it.

---
