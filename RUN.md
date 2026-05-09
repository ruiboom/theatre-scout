# Run

For 2nd-run onwards. First-time setup (`uv sync`) is assumed done.

```bash
cd "/Users/ruiteimao/Documents/CLAUDE SANDBOXES/theatre-scout"

uv run scout scrape          # refresh the local DB (~2 min, listing pages only)
uv run scout serve           # web UI at http://localhost:8000
```

That's the fast loop: scrape, then serve. Or hit the **Refresh** button in the web UI.

## With descriptions (slower)

```bash
uv run scout scrape --enrich --workers 16   # ~3-5 min with parallelism
uv run scout scrape --enrich                # serial enrich, ~25 min
```

The `--workers` flag fans the per-show detail-page fetches across a thread pool. The per-host rate limit (1 req/sec) still applies, so two shows on the same venue still serialize — but venues run in parallel. With 16 workers and ~50 distinct hosts, the enrich step shrinks from ~22 min to a couple of minutes.

Without `--enrich` you get titles and dates from the listing cards only; descriptions populate where the listing exposes them, otherwise stay empty.

## After adapter changes

```bash
uv run scout scrape --theatre park-theatre --replace          # wipe stale rows for that venue first
uv run scout scrape --replace                                  # wipe all stale rows, full re-scrape
```

`--replace` only deletes rows for theatres that *successfully* re-scrape — if a venue's fetch fails, its existing rows stay put.

## Useful one-offs

```bash
uv run scout list                                              # print every known theatre
uv run scout scrape --theatre almeida                          # rescrape one venue
uv run scout scrape --theatre almeida --enrich --replace       # clean refresh of one venue
uv run scout serve --port 8765                                 # custom port
```

## After pulling code changes

```bash
uv sync                                    # re-resolve deps if pyproject changed
uv run pytest                              # confirm nothing broke
```

## Browser binaries (one-time)

7 venues need a real browser to render their listings. Run this once after `uv sync`:

```bash
uv run scrapling install --force
```

Downloads Chromium + Patchright (~500MB).

## Rollback

If anything's gone sideways:

```bash
git reset --hard pre-scrapling-tier-3   # back to known-good Tier 2 (no parallelism)
git reset --hard pre-scrapling-tier-2   # back to Tier 1 (Scrapling but bs4 still in use)
git reset --hard pre-scrapling          # pre-Scrapling entirely (httpx + bs4)
uv sync                                  # always re-sync after a reset
```
