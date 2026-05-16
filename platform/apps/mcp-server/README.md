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
- **`@cloudflare/workers-oauth-provider`** — wraps the worker as an OAuth 2.1 provider so Claude/ChatGPT can connect (see Auth).
- **Hono** as the outer fetch handler (the OAuth provider's default handler — serves the public routes and the consent screen).

## Auth

`/mcp` and `/sse` are **OAuth 2.1 protected**. Claude and ChatGPT both require an auth handshake to add a remote MCP connector, so the worker is fronted by `@cloudflare/workers-oauth-provider`, which serves the discovery metadata (RFC 8414 + RFC 9728), Dynamic Client Registration (RFC 7591), `/token`, and S256 PKCE — i.e. the [MCP authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization). Public routes (`/`, `/health`, `/openapi.json`) stay unauthenticated.

The listings are public, read-only, and there is **no user account system**, so there is no real identity to capture. `/authorize` ([src/index.ts](src/index.ts)) is a single **Authorize** button that issues a token bound to an anonymous principal. The OAuth flow exists purely so the connector handshake completes. If per-user features ever land, federate `/authorize` to a real IdP — the rest of the wiring is unchanged.

State (registered clients, grants, tokens) lives in the `OAUTH_KV` namespace declared in [wrangler.toml](wrangler.toml).

Verify the whole contract against any deployed/dev URL:

```bash
./verify-oauth.sh https://platform-mcp-server.<account>.workers.dev
```

## Dev

```bash
# 1. The worker fetches data from the website's API. Boot the website first.
pnpm --filter website dev          # http://localhost:3000

# 2. Boot the MCP worker (wrangler simulates OAUTH_KV locally — the
#    placeholder id in wrangler.toml is fine for `dev`, not for `deploy`).
pnpm --filter mcp-server dev       # http://localhost:8787/mcp
```

`/mcp` is OAuth-protected, so point an MCP client that speaks the OAuth flow
(Claude/ChatGPT connectors) at `http://localhost:8787/mcp` and complete the
consent screen. Sanity-check the contract directly:

```bash
./verify-oauth.sh http://localhost:8787
```

## Deploy

`wrangler` is a workspace dev-dependency — invoke via `npx wrangler` (no
global pnpm/wrangler needed).

```bash
cd apps/mcp-server
npx wrangler login                        # one-time Cloudflare browser login
npx wrangler kv namespace create OAUTH_KV # paste the printed id into wrangler.toml
npx wrangler deploy
# API_BASE_URL already defaults to the live Vercel deploy in wrangler.toml;
# `npx wrangler secret put API_BASE_URL` only if you want to override it.
# Public URL: https://platform-mcp-server.<account>.workers.dev/mcp
```

Then connect from Claude/ChatGPT — see [DEPLOY.md §4](../../DEPLOY.md) for the
click-path and verification.

## OpenAPI export

The same tool definitions in `src/tools/` are also exported as an OpenAPI document at `/openapi.json` for the Custom GPT. **Don't write a separate spec** — divergence is a class of bug we don't want to hunt.
