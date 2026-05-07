# Run

For 2nd-run onwards. First-time setup (`uv sync`) is assumed done.

```bash
cd "/Users/ruiteimao/Documents/CLAUDE SANDBOXES/theatre-scout"

uv run scout scrape          # refresh the local DB (~2 min, 68 venues)
uv run scout serve           # web UI at http://localhost:8000
```

That's the loop: scrape, then serve. Or hit the **Refresh** button in the web UI to do both in one step.

## Useful one-offs

```bash
uv run scout list                         # print every known theatre
uv run scout scrape --theatre almeida     # rescrape one venue
uv run scout serve --port 8765            # custom port
```

## After pulling code changes

```bash
uv sync                                    # re-resolve deps if pyproject changed
uv run pytest                              # confirm nothing broke
```
