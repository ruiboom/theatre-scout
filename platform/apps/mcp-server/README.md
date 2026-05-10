# mcp-server

Remote MCP server. Wraps the Internal API as six tools for Claude, custom GPTs, and any future agent.

## What it is — and isn't

It's a **thin wrapper**. Per `docs/TOOL_SURFACE.md`:

> The MCP server is a thin wrapper. Each tool maps to one Internal API endpoint. **No business logic in the MCP server itself** — keep it in the API so the website and Custom GPT get the same behaviour.

So this server has zero database access. It only translates MCP tool calls into HTTP requests against `/api/v1/*` and reshapes the result.

## Tools

Six tools, defined in `src/tools/`:

| Tool | Calls | Doc |
|------|-------|-----|
| `search_shows`     | `GET  /api/v1/shows`             | the workhorse |
| `get_show`         | `GET  /api/v1/shows/{id_or_slug}`| full detail |
| `whats_on`         | `GET  /api/v1/whats-on`          | resolves "tonight"/"this_weekend" in Europe/London |
| `recommend_shows`  | `POST /api/v1/recommend`         | vibe → ranked picks with `why` |
| `search_venues`    | `GET  /api/v1/venues`            | by name / area / coords |
| `get_venue`        | `GET  /api/v1/venues/{id_or_slug}` | venue detail + current shows |

Schemas come from `@platform/shared/schemas` so the MCP tool definition and the API input validation can never drift.

## Stack

- **TypeScript** running on **Cloudflare Workers** (boring, cheap, fast cold starts).
- **`agents/mcp`** — Cloudflare's `McpAgent` class — handles Streamable HTTP + Durable Object session storage.
- **`@modelcontextprotocol/sdk`** for the `McpServer` API.
- **Hono** as the outer fetch handler (so non-MCP routes — health, OpenAPI export — share the same worker).

## Dev

```bash
# 1. The worker fetches data from the website's API. Boot the website first.
pnpm --filter website dev          # http://localhost:3000

# 2. Boot the MCP worker
pnpm --filter mcp-server dev       # http://localhost:8787/mcp

# 3. Connect Claude Desktop:
# In claude_desktop_config.json:
{
  "mcpServers": {
    "theatre-scout": {
      "url": "http://localhost:8787/mcp"
    }
  }
}
```

## Deploy

```bash
cd apps/mcp-server
wrangler secret put API_BASE_URL          # https://your-website.example.com/api/v1
wrangler deploy
# Public URL: https://platform-mcp-server.<account>.workers.dev/mcp
```

## OpenAPI export

The same tool definitions in `src/tools/` are also exported as an OpenAPI document at `/openapi.json` for the Custom GPT. **Don't write a separate spec** — divergence is a class of bug we don't want to hunt.
