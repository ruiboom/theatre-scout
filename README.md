# Theatre Scout

A local Python app that scrapes 68 London theatres outside the West End and serves a browseable directory of current and upcoming shows.

## Quick start

```bash
uv sync
uv run scout scrape          # populate the local SQLite DB
uv run scout serve           # http://localhost:8000
```

## CLI

```bash
uv run scout list                          # all known theatres
uv run scout scrape                        # scrape every theatre (~2 min)
uv run scout scrape --theatre almeida      # scrape one
uv run scout serve --port 8765             # custom port
uv run scout --version
```

Data lives in `data/theatre-scout.db` (SQLite, gitignored). Re-running `scrape` upserts shows by `(theatre_slug, title, start_date)` and records a row per `scrape_runs` so you can see what worked.

## Web UI

- `/` — theatres grouped by category, with show counts
- `/theatres/<slug>` — that theatre's upcoming shows
- `/shows` — every upcoming show, with search + type/category filters
- `Refresh` button (POST `/refresh`) — runs a full scrape

## Project layout

```
theatre-scout/
├── theatres.yaml              # 68 venues — single source of truth
├── scout/
│   ├── cli.py                 # Typer commands
│   ├── db.py                  # SQLite schema + queries (no ORM)
│   ├── http.py                # rate-limited, robots-aware client
│   ├── models.py              # Pydantic Show / Theatre / ScrapeRun
│   ├── scraper.py             # orchestration (run_one / run_all)
│   ├── classify.py            # heuristic show-type classifier
│   ├── adapters/
│   │   ├── base.py            # BaseAdapter (abstract parse → list[Show])
│   │   ├── _generic.py        # GenericAdapter (JSON-LD first, then card selectors)
│   │   ├── _jsonld.py         # schema.org Event extractor
│   │   ├── _html.py           # date/text helpers
│   │   ├── almeida.py         # bespoke pilot adapter
│   │   └── bulk.py            # 67 thin GenericAdapter subclasses
│   └── web/                   # FastAPI app + Jinja templates
└── tests/                     # pytest, with saved HTML fixtures
```

See [CLAUDE.md](CLAUDE.md) for architecture rationale and [BUILD.md](BUILD.md) for the milestone plan that built this.

## Adding a new venue

1. Add to `theatres.yaml` with a unique kebab-case slug.
2. Save a representative HTML sample to `tests/fixtures/<slug>.html`.
3. Either:
   - **Generic case**: add an entry to `scout/adapters/bulk.py` with `(slug, listings_url, css_selector)`.
   - **Bespoke**: write `scout/adapters/<slug>.py` subclassing `BaseAdapter`, plus `tests/adapters/test_<slug>.py`.

`uv run scout scrape --theatre <slug>` against the live site to verify.

## Development

```bash
uv run pytest                  # all tests (~3 sec)
uv run ruff format .           # format
uv run ruff check .            # lint
uv run mypy scout              # type check
```

The `tests/test_layering.py` guard ensures lower layers (`db.py`, `models.py`, `scraper.py`) don't accidentally import `typer` / `fastapi`.

## Known limitations

- 5 venues are JavaScript-rendered (Yard, Vaults, Seven Dials, etc.) and need Playwright to scrape — currently registered but return 0 shows.
- 2 venues (Hen & Chickens, Tabard) had network/SSL issues during the last live scrape — registered but unreliable.
- Quality of generic-adapter output varies (e.g. Pleasance returns "Book tickets for X" titles). Per-venue cleanup is straightforward in a custom adapter.
- See [QUESTION_LOG.md](QUESTION_LOG.md) for autonomous decisions taken during the build.
