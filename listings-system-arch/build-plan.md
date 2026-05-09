# Build plan

Three phases. The press moment lives in Phase 3, not Phase 1.

---

## Phase 1 — Ship the website (now → 1 Sept 2026)

- Polish, About page, soft launch (no press yet — save the moment for Phase 3)
- Email capture from day one (Beehiiv or Buttondown)
- Cold-email 10 theatres pitching a distribution partnership
- SEO foundation: structured data per show, neighbourhood + genre landing pages
- Start being useful in r/london, r/uktheatre, theatre Twitter — not promoting, recommending

## Phase 2 — Build the MCP server (Sept → Oct)

- Day 1: read modelcontextprotocol.io and 2–3 example servers
- Define the tool surface (see `TOOL_SURFACE.md`) — this is the design work that matters most
- Pick an SDK — TypeScript or Python (both Anthropic-maintained)
- Build read-only first; no auth needed since listings are public
- **Build it as a remote MCP server (HTTP), not stdio** — stdio means users install something locally, which kills adoption
- Deploy somewhere boring and cheap (Cloudflare Workers, Railway, Fly)
- Test from Claude Desktop, then claude.ai
- In parallel: ship a Custom GPT pointing at the same backend — same data, second storefront, near-zero extra work

## Phase 3 — AI-native launch moment (Oct/Nov)

- **This is the press release moment, not 1 September.** Story rewrites itself: *"Solo dev builds AI-native discovery for London's overlooked theatre scene."*
- Submit to Claude's app directory and the MCP registries
- Re-pitch theatre partners with the new angle (*"ask Claude what's on at our venue tonight"*)
- Demo video: someone asks Claude *"what should I see in Peckham tonight under £15?"* and gets a real, specific, good answer

---

## Things worth knowing before starting Phase 2

- MCP is a young-ish protocol (released late 2024). Tooling has matured but expect rough edges.
- Python and TypeScript SDKs are the main paths in. TS is slightly more battle-tested for remote servers.
- The interesting design work isn't the code — it's the **tool surface**. Bad tool design = AI can't use the server well = bad answers = no audience. See `TOOL_SURFACE.md`.
- Discovery for now lives mostly in the Claude app directory. ChatGPT MCP support is improving — bet on it but don't wait for it.

## Why this sequencing works

A pure listings site is hard to get press for — there's no story. By stacking the AI layer on top and saving the press for that moment, you get one strong launch instead of two weak ones. The website also gets ~2 months in soft-launch where the audience is small and forgiving — perfect for ironing out data quality issues before you put it under any real load.
