# Theatre Scout — Build Plan

This is the execution companion to [`CLAUDE.md`](CLAUDE.md). CLAUDE.md is *what* we're building; this file is *how and in what order*.

## Working principles (apply to every milestone)

- **TDD, strictly.** For each task: write the failing test first → see red → write the minimum code to green → refactor. No production code without a failing test driving it.
- **Functional bias.** Parsers, transformations, and orchestration are pure functions of inputs. Side effects (HTTP, DB, filesystem, stdout, time) live in thin edge modules and are dependency-injected, so tests stay fast and deterministic.
- **Lean.** No abstraction without two real callers. No error handling for cases that can't happen. No config flag without a concrete need today. If three adapters duplicate a pattern, *then* extract a helper — not before.
- **Refactor as a discrete milestone-end step.** Acceptable to leave ugly working code mid-milestone. The refactor pass at the end is the only place to clean up.
- **Small commits.** One coherent change per commit; mix of `test:`, `feat:`, `refactor:` prefixes. One commit per adapter during M8.

## Milestone roadmap

| # | Name | Est. | Outcome |
|---|---|---|---|
| M0 | Project skeleton | 30 min | `pytest` runs; `scout --version` prints |
| M1 | Theatre data + models | 1 h | `theatres.yaml` validates and loads into 68 `Theatre` objects |
| M2 | SQLite persistence | 1.5 h | `Show`/`Theatre`/`ScrapeRun` round-trip; re-insert dedupes |
| M3 | HTTP layer | 1.5 h | Polite client: rate-limited, cached, robots-aware |
| M4 | Adapter framework | 1 h | Registry + JSON-LD helper + `BaseAdapter` |
| M5 | Pilot adapter (Almeida) | 1.5 h | One theatre scraped end-to-end into DB |
| M6 | Orchestrator + `scout scrape` | 1.5 h | Full-run CLI with failure isolation |
| M7 | Web UI MVP | 2 h | `scout serve` browseable directory + refresh button |
| M8 | Adapter rollout (×66) | ongoing | All theatres covered, fixture + test each |
| M9 | Polish | 2–3 h | Search/filter UI, type classifier, README |

Framework + first adapter: ~12 h. Adapter rollout is its own ongoing thing (estimate ~30 min per simple adapter, 1–2 h per JS-heavy one).

---

## M0 — Project skeleton

**Tests first** (`tests/test_skeleton.py`):
- `test_package_imports` — `import scout` succeeds
- `test_cli_version` — Typer `CliRunner` invocation of `--version` exits 0 and prints `0.1.0`

**Code**:
- `pyproject.toml` — uv; runtime deps: `typer`, `pydantic`, `httpx`, `beautifulsoup4`, `lxml`, `pyyaml`, `fastapi`, `jinja2`, `uvicorn`; dev: `pytest`, `ruff`, `mypy`
- `scout/__init__.py` — `__version__ = "0.1.0"`
- `scout/cli.py` — Typer app with `--version` callback
- `.gitignore` — `data/`, `.cache/`, `.venv/`, `__pycache__/`, `*.db`
- `pytest` config in `pyproject.toml`

**Refactor**: none.

**Done when**: `uv run pytest` green; `uv run scout --version` prints `0.1.0`.

---

## M1 — Theatre data + models

**Tests first** (`tests/test_theatres.py`):
- yaml file loads
- exactly 68 entries
- all slugs unique and kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`)
- categories ∈ `{major, mid, fringe, outer}` with counts `{18, 19, 19, 12}`
- all `url` values are `https://`
- `postcode_prefix` matches `^[A-Z]{1,2}\d{1,2}[A-Z]?$`

**Code**:
- `scout/models.py` — frozen Pydantic `Theatre`
- `scout/theatres.py` — pure `load(path) -> list[Theatre]`
- `theatres.yaml` — hand-built from the list in CLAUDE.md, deterministic slugs (`almeida`, `bridge-theatre`, `theatre-royal-stratford-east`, …)

**Refactor**: confirm `load` is pure (no module-level state); collapse model boilerplate.

---

## M2 — SQLite persistence

**Tests first** (`tests/test_db.py`, all use `:memory:`):
- `init_schema(conn)` is idempotent
- `upsert_theatres(conn, theatres)` is idempotent
- `insert_show(conn, show)` followed by re-insert of same `(theatre_slug, title, start_date)` → 1 row, `last_seen_at` updated
- `query_upcoming(conn, today)` filters by `end_date >= today`, sorted by `start_date`
- `query_by_theatre(conn, slug)` filters
- `record_scrape_run(conn, run)` persists status + counts

**Code**:
- `scout/models.py` — add `Show` (frozen), `ScrapeRun`
- `scout/db.py` — `connect`, `init_schema`, plus a flat functional API. Raw SQL, no ORM.

**Refactor**: extract `_row_to_show` / `_show_to_row` only if duplication shows up. Keep query functions one-liners.

---

## M3 — HTTP layer

**Tests first** (`tests/test_http.py`):
- `RateLimiter`: with an injected fake clock, two requests to same host are ≥ 1 s apart; different hosts independent
- `Cache`: miss writes; subsequent hit doesn't call the underlying fetcher (counter assertion)
- `is_allowed(url, robots_txt)`: respects a fixture
- `Client.get(url)`: integrates the three; sets `User-Agent: TheatreScout/0.1 (+local research bot)`

**Code**:
- `scout/http.py` — `RateLimiter`, `Cache` (env-toggled, file-backed), `is_allowed`, `Client.get(url) -> Response | None` (None ⇒ robots disallowed)

**Refactor**: target < 150 lines for the whole module. Remove anything speculative.

---

## M4 — Adapter framework

**Tests first** (`tests/test_adapter_framework.py`, `tests/test_jsonld.py`):
- registry: `get_adapter("almeida")` returns the class; unknown slug raises
- `parse_jsonld(html, base_url) -> list[Show]`: extracts schema.org `Event` / `TheaterEvent`; ignores unrelated types; handles arrays and `@graph`

**Code**:
- `scout/adapters/base.py` — `BaseAdapter` with abstract `parse(html, base_url)` and concrete `fetch(client)` that wraps `client.get` + `parse`
- `scout/adapters/_jsonld.py` — `parse_jsonld`
- `scout/adapters/__init__.py` — registry built from import side-effects

**Refactor**: confirm `parse` is pure (no `client`, no `datetime.now()`). Move any `now`-style needs into the orchestrator.

---

## M5 — Pilot adapter: Almeida

**Tests first**:
- `tests/fixtures/almeida.html` — saved once with curl
- `tests/adapters/test_almeida.py` — `parse(fixture, base_url)` returns the expected `Show` list
- `tests/test_scrape_e2e.py` — monkeypatch `Client.get` to return the fixture, run a stub orchestrator, assert DB rows

**Code**:
- `scout/adapters/almeida.py` — JSON-LD first, CSS selectors as fallback
- minimal stub of `scout/scraper.py::run_one(slug, client, conn)` so the e2e test passes

**Refactor**: any selector-walking pattern that looks reusable → `scout/adapters/_html.py`.

---

## M6 — Orchestrator + `scout scrape`

**Tests first** (`tests/test_scraper.py`, `tests/test_cli_scrape.py`):
- `run_one(slug, client, conn) -> ScrapeRun(status="success", shows_found=N)`
- adapter raises → `ScrapeRun(status="failed", error=...)`, other theatres unaffected
- `run_all(client, conn)` returns one `ScrapeRun` per registered adapter
- `scout scrape`: exit 0 on success, exit 1 if all failed
- `scout scrape --theatre almeida`: only runs that one

**Code**:
- `scout/scraper.py` — `run_one`, `run_all`; pure orchestration; deps injected
- `scout/cli.py` — `scrape` command

**Refactor**: forbid `import typer` and `import fastapi` in `scraper.py`. Verify with a meta-test (`tests/test_layering.py`).

---

## M7 — Web UI MVP

**Tests first** (`tests/test_web.py`, FastAPI `TestClient`):
- `GET /` → 200, response body contains category names + counts
- `GET /theatres/{slug}` → 200, lists that theatre's shows
- `GET /shows` → 200, upcoming shows ordered by `start_date`
- `POST /refresh` → 303 redirect; mocked scraper called once

**Code**:
- `scout/web/app.py` — FastAPI app; DB connection via `Depends`
- `scout/web/templates/{base,index,theatre,shows}.html` — Jinja2, minimal
- `scout/web/static/style.css` — ~50 lines plain CSS
- `scout/cli.py` — `serve` command (programmatic uvicorn)

**Refactor**: extract `format_date`, `format_price` template filters.

---

## M8 — Adapter rollout (the long tail)

**Order**: major → mid → fringe → outer (`major` first because high-value content; `outer` last because some are receiving houses with overlapping listings).

**Per-adapter loop** — this *is* the TDD repetition:

1. `curl -A "TheatreScout/0.1 (+local research bot)" <url> > tests/fixtures/<slug>.html`
2. Eyeball: JSON-LD present? CSS selectors? JS-rendered?
3. Write `tests/adapters/test_<slug>.py` with expected `Show` list (red).
4. Write `scout/adapters/<slug>.py` until green.
5. Register in `scout/adapters/__init__.py`.
6. `uv run scout scrape --theatre <slug>` against live site — sanity check.
7. Commit.

**Refactor checkpoints**: every 5 adapters, scan for duplication. Likely extractions to `scout/adapters/_common.py`:
- date-range parsing (`"4 May – 12 Jul 2026"` → `(date, date)`)
- price-range parsing (`"£18 – £52"` → `(1800, 5200)` in pence)
- show-type inference from text

**JS-heavy sites**: when `httpx` returns near-empty body, add `client.render(url)` using Playwright. Mark the adapter `requires_js = True` so the orchestrator launches a browser only when needed.

---

## M9 — Polish

- Search box + filters (category, type, date range) in the web UI.
- Heuristic show-type classifier (~20 lines of regex on title/description).
- `README.md` for first-time local users.
- Optional `scout doctor` — pings every URL in `theatres.yaml`, reports 404s.

---

## Definition of done (whole project)

- `uv run pytest` green.
- `uv run ruff check && uv run ruff format --check && uv run mypy scout` green.
- All 68 adapters present, each with a fixture and parse test.
- `uv run scout scrape` completes a full run with ≥ 90% theatres in `success` status.
- `uv run scout serve` serves a browseable, searchable directory.

## What we are deliberately NOT doing

- No user accounts, auth, multi-tenant.
- No background job runner (cron, celery). Manual triggers only.
- No deploy story. Local app, full stop.
- No live ticket prices / availability — too brittle, just summary ranges if visible.
- No social/sharing/export features in v1.
