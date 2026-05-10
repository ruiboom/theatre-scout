import { McpAgent } from 'agents/mcp';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Hono } from 'hono';

import { ApiClient } from './api-client.js';
import { registerTools } from './tools.js';

interface Env {
  API_BASE_URL: string;
  // `agents/mcp` looks up the agent's Durable Object via this binding name.
  MCP_OBJECT: DurableObjectNamespace;
}

/**
 * The MCP agent. Per Cloudflare's `agents/mcp` pattern, this class is a
 * Durable Object — sessions are persisted across reconnects.
 *
 * `init()` is called once per session: register tools here.
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

const app = new Hono<{ Bindings: Env }>();

app.get('/', (c) =>
  c.json({
    name: 'platform-mcp-server',
    description: 'Remote MCP server for the listings platform.',
    endpoints: {
      mcp: '/mcp',
      health: '/health',
      openapi: '/openapi.json',
    },
  }),
);

app.get('/health', (c) => c.json({ ok: true }));

// Streamable HTTP MCP endpoint
app.all('/mcp', (c) =>
  ListingsMCP.serve('/mcp').fetch(c.req.raw, c.env, c.executionCtx),
);

// SSE alternative (older clients) — same agent, different transport.
app.all('/sse', (c) =>
  ListingsMCP.serveSSE('/sse').fetch(c.req.raw, c.env, c.executionCtx),
);

app.get('/openapi.json', (c) =>
  c.json({
    openapi: '3.1.0',
    info: { title: 'Listings API', version: '0.0.1' },
    servers: [{ url: c.env.API_BASE_URL }],
    // TODO: derive paths from @platform/shared/schemas so the GPT and MCP
    // server share one source of truth. Stub for now.
    paths: {},
  }),
);

export default app;
