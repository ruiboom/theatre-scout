import { McpAgent } from 'agents/mcp';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Hono } from 'hono';
import OAuthProvider from '@cloudflare/workers-oauth-provider';
import type { OAuthHelpers } from '@cloudflare/workers-oauth-provider';

import { ApiClient } from './api-client.js';
import { registerTools } from './tools.js';

interface Env {
  API_BASE_URL: string;
  // `agents/mcp` looks up the agent's Durable Object via this binding name.
  MCP_OBJECT: DurableObjectNamespace;
  // OAuth provider state (registered clients, grants, tokens).
  OAUTH_KV: KVNamespace;
  // Injected by OAuthProvider into env for the default handler to call back.
  OAUTH_PROVIDER: OAuthHelpers;
}

/**
 * The MCP agent. Per Cloudflare's `agents/mcp` pattern, this class is a
 * Durable Object — sessions are persisted across reconnects.
 *
 * Reached only after OAuthProvider has validated a bearer token, so every
 * tool call is authenticated. `init()` is called once per session.
 */
export class ListingsMCP extends McpAgent<Env> {
  server = new McpServer({
    name: 'theatre-scout',
    version: '0.0.1',
  });

  async init() {
    const api = new ApiClient(this.env.API_BASE_URL);
    registerTools(this.server, api);
  }
}

/**
 * The default handler: every request that is NOT a token-protected API route
 * and NOT a provider-implemented OAuth endpoint (`/token`, `/register`,
 * `/.well-known/*`). Serves the public info/health routes and the OAuth
 * consent screen.
 */
const app = new Hono<{ Bindings: Env }>();

app.get('/', (c) =>
  c.json({
    name: 'platform-mcp-server',
    description: 'Remote MCP server for the listings platform.',
    endpoints: {
      mcp: '/mcp',
      health: '/health',
      openapi: '/openapi.json',
      authorize: '/authorize',
      token: '/token',
      register: '/register',
      oauth_metadata: '/.well-known/oauth-authorization-server',
    },
  }),
);

app.get('/health', (c) => c.json({ ok: true }));

// The canonical OpenAPI spec lives next to the API on Vercel. Forward to it.
app.get('/openapi.json', (c) => {
  const target = c.env.API_BASE_URL.replace(/\/v1\/?$/, '') + '/openapi';
  return Response.redirect(target, 302);
});

/**
 * OAuth consent screen. OAuthProvider advertises this as `authorizeEndpoint`
 * in the discovery metadata but does NOT implement it — the app owns the UI.
 *
 * The data this server exposes is public, read-only theatre listings and
 * there is no user account system, so there is no real identity to capture.
 * The consent step exists purely so the OAuth handshake that Claude/ChatGPT
 * require completes: the user sees who is connecting and clicks Authorize,
 * and we issue a token bound to an anonymous principal.
 */
app.all('/authorize', async (c) => {
  // `parseAuthRequest` reads the OAuth params from the query string, so the
  // consent form posts back to the same URL with the query string intact.
  const oauthReq = await c.env.OAUTH_PROVIDER.parseAuthRequest(c.req.raw);
  const client = await c.env.OAUTH_PROVIDER.lookupClient(oauthReq.clientId);
  const clientName = client?.clientName ?? oauthReq.clientId;

  if (c.req.method === 'POST') {
    const { redirectTo } = await c.env.OAUTH_PROVIDER.completeAuthorization({
      request: oauthReq,
      userId: 'anonymous',
      metadata: { client: clientName },
      scope: oauthReq.scope,
      props: { anonymous: true },
    });
    return Response.redirect(redirectTo, 302);
  }

  const url = new URL(c.req.url);
  return c.html(consentPage(clientName, url.pathname + url.search));
});

function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (ch) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[ch] as string,
  );
}

function consentPage(clientName: string, action: string): string {
  const name = escapeHtml(clientName);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Authorize Theatre Scout</title>
<style>
  body { font: 16px/1.5 system-ui, sans-serif; margin: 0; background: #faf8f5;
         color: #1a1a1a; display: grid; place-items: center; min-height: 100vh; }
  .card { background: #fff; max-width: 26rem; padding: 2rem; border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  h1 { font-size: 1.25rem; margin: 0 0 .5rem; }
  p { color: #555; margin: .5rem 0; }
  strong { color: #1a1a1a; }
  button { font: inherit; font-weight: 600; width: 100%; padding: .75rem;
           margin-top: 1rem; border: 0; border-radius: 8px; cursor: pointer;
           background: #c0392b; color: #fff; }
  button:hover { background: #a93226; }
  .note { font-size: .85rem; color: #888; margin-top: 1rem; }
</style>
</head>
<body>
  <div class="card">
    <h1>Connect to Theatre Scout</h1>
    <p><strong>${name}</strong> wants to access the Theatre Scout listings
       directory — current and upcoming productions at London theatres outside
       the West End.</p>
    <p>This grants read-only access to public listings data. No personal
       account or private data is involved.</p>
    <form method="POST" action="${escapeHtml(action)}">
      <button type="submit">Authorize</button>
    </form>
    <p class="note">You can revoke access at any time from the connecting
       application.</p>
  </div>
</body>
</html>`;
}

export default new OAuthProvider<Env>({
  apiHandlers: {
    '/mcp': ListingsMCP.serve('/mcp'),
    '/sse': ListingsMCP.serveSSE('/sse'),
  },
  defaultHandler: app as unknown as ExportedHandler<Env>,
  authorizeEndpoint: '/authorize',
  tokenEndpoint: '/token',
  clientRegistrationEndpoint: '/register',
  scopesSupported: ['listings.read'],
  // OAuth 2.1: reject the weaker plain PKCE method; require S256.
  allowPlainPKCE: false,
});
