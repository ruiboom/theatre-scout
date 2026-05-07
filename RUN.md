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
uv run scout scrape --enrich   # fetches each show's detail page, ~15-20 min
```

Use this overnight or when you want full descriptions. Without `--enrich` you get the title and dates extracted from the listing card; descriptions populate where the listing exposes them, otherwise stay empty.

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
