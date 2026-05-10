# scrapers

Python ingestion. One adapter per venue. The orchestrator runs adapters in parallel (across distinct domains), each adapter returns a list of normalised `Show` records, the writer upserts them into Postgres.

## Why Python here, TypeScript everywhere else?

The HTML-parsing surface is large and messy. Python's `httpx` + `bs4` + `lxml` + `scrapling` ecosystem is what we already know — switching to Node would be principled but produce no business value.

Surfaces (website, MCP server) stay TypeScript because they share types with `@platform/shared`. Scrapers can be Python because their interface to the rest of the system is the database, not a TypeScript module.

## Layout

```
scrapers/
├── cli.py              `scrape all`, `scrape venue <slug>`, `scrape list`
├── base.py             BaseAdapter (abstract) — every adapter is one class
├── http.py             httpx client w/ rate limiting + dev cache
├── normalize.py        free-form scraped dicts → strict Show / Performance
├── writer.py           psycopg upsert into venues/shows/performances
├── runner.py           orchestrator: load venues, dispatch, record runs
└── adapters/
    ├── __init__.py     registry: slug → adapter class
    └── example.py      placeholder, copy when adding a new venue
```

## Adding a venue

1. Add it to `../../theatres.yaml` with a unique kebab-case `slug`.
2. Save a representative HTML sample to `tests/fixtures/<slug>.html`.
3. Create `scrapers/adapters/<slug>.py` subclassing `BaseAdapter`.
4. Register it in `scrapers/adapters/__init__.py`.
5. Write `tests/adapters/test_<slug>.py` that loads the fixture and asserts the parsed `Show` dicts.
6. `uv run pytest tests/adapters/test_<slug>.py` and `uv run scrape venue <slug>`.

## Run

```bash
cp ../../.env.example .env
uv sync
uv run scrape list                  # show registered venues
uv run scrape venue almeida         # one
uv run scrape all                   # all of them, in parallel across domains
```

## Conventions (from `docs/ARCHITECTURE.md`)

- 1 req/sec per host, token-bucketed.
- User-Agent: `AnywhereBuTheWestEnd/0.1 (+https://anywhere.example.com/bot)`
- Honour robots.txt; skip disallowed paths and warn.
- Cache responses for 1 hour in dev so iteration doesn't hammer venues.
- Prefer `application/ld+json` `Event` / `TheaterEvent`. Fall back to HTML.
- One failed adapter does not crash the run; orchestrator records a `failed` ScrapeRun and moves on.
