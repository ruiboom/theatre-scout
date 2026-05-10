# scrapers

Python ingestion. One adapter per venue. Architecture mirrors `scout/`'s Tier-3 design (Scrapling + 3-phase orchestrator + per-adapter `enrich()` hook) so the existing 30+ scout adapters port cleanly.

## Stack

- **Scrapling** — `FetcherSession` (curl_cffi + Chrome TLS impersonation) for the fast path; `StealthySession` (Patchright headless browser) for JS-rendered or anti-bot venues.
- **`scrapling.parser.Selector`** — replaces `bs4` / `lxml` for HTML walking. Adapter code is identical to scout.
- **psycopg** — Postgres writes. The writer is the single place that translates the adapter-facing `Show` (scout-shaped: `theatre_slug`, `url`, `price_min` in pence) onto platform DB columns (`venue_id`, `booking_url`, `price_min_pence`, etc.).

## Layout

```
scrapers/
├── cli.py            `scrape list / venue <slug> / all / sync-venues`
├── classify.py       heuristic show-type classifier
├── enrich.py         pure description + image extractors
├── http.py           Scrapling-backed Client (rate-limit, robots, stealth thread)
├── models.py         Show, Theatre, ScrapeRun (mirror scout's pydantic shape)
├── runner.py         3-phase orchestrator with round-robin enrich
├── text.py           clean_text / clean_description / slugify
├── writer.py         psycopg writes; Show -> DB column mapping
└── adapters/
    ├── __init__.py   load_all() — imports bespoke modules + bulk
    ├── base.py       BaseAdapter (parse + enrich + requires_js + fetch)
    ├── registry.py   @register decorator
    ├── _generic.py   GenericAdapter (JSON-LD first, then card CSS)
    ├── _html.py      parse_date_range — British date-range parser
    ├── _jsonld.py    schema.org Event / TheaterEvent extractor
    ├── bulk.py       (slug, url, css_selector) tuples → GenericAdapter subclasses
    └── example.py    bespoke template
```

## Adding a venue

Two paths, same as scout:

1. **Generic** (most venues): add `("my-venue", "https://example.com/whats-on", 'a[href*="/event/"]')` to `bulk._ENTRIES`. The selector should land on cards that contain a title and link.
2. **Bespoke** (when generic fails — button-text titles, JS-rendered, paginated): copy `adapters/example.py` to `adapters/<slug>.py`, override `parse()` (and optionally `enrich()`), set `requires_js = True` if the listing needs the stealth path, and add `from . import <slug>` to `adapters/__init__.py::load_all()`.

Either way, you also need a row in the venues table — populate via `scrape sync-venues theatres.yaml` once, then it's there.

## Run

```bash
cp ../../.env.example .env

# (optional) install Patchright's bundled Chromium for stealth fetches
uv run scrapling install --force

uv sync
uv run scrape list                                       # show registered venues
uv run scrape venue example                              # one venue, listings only
uv run scrape venue example --enrich --replace --workers 4   # full pipeline, single venue
uv run scrape all --enrich --replace --workers 16        # full pipeline, all venues
```

## Conventions

- 1 req/sec per host, token-bucketed (`http.py::RateLimiter`).
- User-Agent: `TheatreScout/0.1 (+https://theatre-scout-zunz.vercel.app)`.
- Honour robots.txt; skip disallowed paths with a warning.
- Prefer schema.org JSON-LD (`Event` / `TheaterEvent`); fall back to per-venue CSS.
- One failed adapter never crashes the run — the orchestrator records a `failed` ScrapeRun for that venue and moves on.
- Stealth fetches all funnel through one dedicated browser-owner thread. Patchright greenlets bind to whichever thread opens the session, so we can't share across worker threads.
- Adapters are pure functions of `(html, base_url) -> list[Show]`. Tests load saved HTML fixtures and assert the parsed records — no network.

## Porting from scout

The adapter-facing API is byte-identical to scout's (same `BaseAdapter` shape, same `Show` fields, same `parse_jsonld` / `parse_date_range` helpers). Porting an adapter means:

1. Copy `scout/adapters/<slug>.py` to `platform/apps/scrapers/scrapers/adapters/<slug>.py`.
2. Update imports (`scout.foo` → `..foo` or `.foo`).
3. Add `@register` on the class.
4. Add the import in `adapters/__init__.py::load_all()`.

That's the whole port. The 30+ scout adapters can move across one commit at a time.
