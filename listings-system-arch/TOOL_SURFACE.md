# TOOL_SURFACE.md

## Purpose

This document defines the tool API the MCP server exposes to AI clients (Claude, Custom GPT via OpenAPI, future agents). It is the contract between the listings database and any conversational interface that consumes it.

When the AI gives a great answer, it's because the tools made it easy. When it gives a bad one, the tool surface is usually why. Treat this file as the most important design artefact in the project.

---

## Design principles

1. **Few tools, well-shaped.** Six tools cover all expected use cases. Resist adding more — extend parameters instead.
2. **Consistent return shapes.** A `Show` always looks the same regardless of which tool returned it. Same for `Venue`. AIs are unforgiving of inconsistency.
3. **Sensible defaults.** `search_shows()` with no parameters returns this week's shows, sorted by date. The AI shouldn't need to specify everything.
4. **Reasoning-friendly returns.** Include fields that help the AI explain its answer (price range, genres, content warnings, short description). The AI is most useful when it can reason aloud.
5. **Fail loudly, not silently.** Empty results return `{ shows: [], total: 0 }`, never `null`. Bad parameters return a 400 with a clear message.

---

## Common types

Defined once and reused across all tool returns.

```ts
type Show = {
  id: string                       // stable identifier
  slug: string                     // url-friendly
  title: string
  venue: VenueSummary              // always inlined for context
  description_short: string        // 1–2 sentences
  genres: string[]                 // e.g. ["comedy", "experimental"]
  tags: string[]                   // e.g. ["queer", "political", "one-person"]
  price_min: number                // GBP
  price_max: number
  next_performance: string | null  // ISO 8601, null if none upcoming
  performance_count: number        // count of upcoming performances
  duration_minutes: number | null
  age_rating: string | null        // e.g. "14+", "PG"
  content_warnings: string[]
  booking_url: string
}

type VenueSummary = {
  id: string
  slug: string
  name: string
  neighbourhood: string            // e.g. "Hackney", "Battersea"
  nearest_tube: string | null
}

type Venue = VenueSummary & {
  description: string
  capacity: number | null
  address: string
  lat: number
  lng: number
  website: string
  current_shows_count: number
}
```

---

## Tools

### `search_shows`

**Purpose:** Flexible search across all listings. The workhorse.

**When to use:** Any combination of filters — date range, location, price, genre.

**Parameters:**

| name | type | required | description |
|------|------|----------|-------------|
| `date_from` | ISO date | no | defaults to today |
| `date_to` | ISO date | no | defaults to `date_from` + 7 days |
| `neighbourhood` | string | no | e.g. `"Hackney"` |
| `near` | `{lat, lng, radius_km}` | no | proximity search |
| `max_price` | number | no | GBP |
| `min_price` | number | no | GBP, defaults to 0 |
| `genres` | string[] | no | match any |
| `tags` | string[] | no | match any |
| `venue_ids` | string[] | no | restrict to specific venues |
| `limit` | number | no | default 20, max 50 |

**Returns:** `{ shows: Show[], total: number }`

**Example:**
```js
search_shows({
  neighbourhood: "Hackney",
  date_from: "2026-09-12",
  date_to: "2026-09-14",
  max_price: 20
})
// → { shows: [...3 shows...], total: 3 }
```

---

### `get_show`

**Purpose:** Full detail for a single show.

**When to use:** User asks about a specific show by name, or after a search result.

**Parameters:** `show_id` (string) OR `slug` (string). Exactly one required.

**Returns:** A `Show` extended with:
- `description_full` — longer description (3–5 paragraphs where available)
- `performances` — array of `{ datetime, available_tickets_estimate, sold_out }`
- `reviews_summary` — optional, if aggregated
- `creators` — `{ writer, director, cast[] }` where known

---

### `whats_on`

**Purpose:** Convenience tool for the most common AI question: *"what's on tonight / this weekend?"*

**When to use:** User asks about a *named* time window without giving exact dates.

**Parameters:**

| name | type | required | description |
|------|------|----------|-------------|
| `when` | enum | yes | `tonight` \| `tomorrow` \| `this_weekend` \| `next_weekend` \| `this_week` |
| `near` | string OR `{lat, lng}` | no | neighbourhood name or coords |
| `max_price` | number | no | GBP |

**Returns:** `{ shows: Show[], total: number, window: { from, to } }`

**Note:** Returns the resolved window so the AI can confirm it back to the user (*"Here's what's on this weekend, 12–14 September..."*). All time math uses `Europe/London`.

---

### `recommend_shows`

**Purpose:** Mood/vibe-based discovery. The "take a punt" tool — this is what differentiates an AI interface from a listings grid.

**When to use:** User asks for a recommendation by feel, mood, or vague description. *"Something weird," "a good first date show," "intense and political," "make me laugh."*

**Parameters:**

| name | type | required | description |
|------|------|----------|-------------|
| `vibe` | string | yes | natural language description |
| `constraints` | object | no | `{ date_from, date_to, max_price, neighbourhood, near }` |
| `exclude_genres` | string[] | no | e.g. `["shakespeare"]` |
| `limit` | number | no | default 5 |

**Returns:**
```ts
{
  recommendations: Array<{
    show: Show,
    why: string   // 1–2 sentence explanation, generated server-side
  }>
}
```

**Note:** The `why` field is critical — it's what lets the AI present a recommendation as a real recommendation, not just a search result. Generating it server-side (small LLM call or rule-based on tags) keeps the client AI's job simple and the explanations consistent.

---

### `search_venues`

**Purpose:** Find venues by name, area, or proximity.

**When to use:** *"What venues are in Camden?"* / *"Where's the Bush Theatre?"* / *"Pub theatres in Stoke Newington?"*

**Parameters:**

| name | type | required | description |
|------|------|----------|-------------|
| `query` | string | no | name match |
| `neighbourhood` | string | no | |
| `near` | `{lat, lng, radius_km}` | no | |
| `limit` | number | no | default 20 |

**Returns:** `{ venues: VenueSummary[], total: number }`

---

### `get_venue`

**Purpose:** Full venue details, optionally with current programming.

**When to use:** User wants to know about a specific venue, or asks *"what's on at [venue]?"*

**Parameters:** `venue_id` (string) OR `slug` (string), plus optional `include_shows` (boolean, default `true`).

**Returns:** `Venue` extended with `current_shows: Show[]` when `include_shows` is true.

---

## Example user → AI → tool flows

**User:** *"What's on tonight near London Bridge?"*
→ AI calls `whats_on({ when: "tonight", near: "London Bridge" })`
→ Gets 3–4 shows, presents conversationally with prices and short descriptions.

**User:** *"I want something weird and political, under £15"*
→ AI calls `recommend_shows({ vibe: "weird and political", constraints: { max_price: 15 } })`
→ Gets 3–5 shows each with a `why`, presents as a curated list.

**User:** *"Tell me more about that second one"*
→ AI calls `get_show({ show_id: "..." })`
→ Full description, performances, content warnings — AI summarises.

**User:** *"What's the Bush Theatre putting on this autumn?"*
→ AI calls `get_venue({ slug: "bush-theatre" })`
→ Venue info + current shows, AI summarises programming themes.

---

## Versioning

- Tool signatures are versioned via the MCP server URL (`/mcp/v1`).
- Breaking changes (renaming params, removing tools) require a new version.
- Additive changes (new optional params, new fields in returns) are non-breaking.
- Annotate deprecations here as `deprecated_in: v2`.

---

## Testing (TDD)

Each tool has three layers of test. Write them in this order.

**1. Schema tests.** Input validation; output shape conforms to the `Show` / `Venue` types above. Use `zod` (TypeScript) or `pydantic` (Python) so the schema *is* the test.

**2. Behaviour tests.** Golden inputs → expected outputs against fixtures in a test database. One fixture covers most cases:
- 3 venues across different neighbourhoods
- 6 shows across genres, prices, dates
- Performances spanning past, today, this week, next month

**3. AI-loop tests (end-to-end).** A known user prompt is sent through Claude with the MCP server connected; the tool calls and final answer are checked. Slow — run nightly on CI, not per-commit. Catches design issues no unit test ever will.

**Critical cases to write first:**
- `search_shows` with no params returns this week's shows in date order
- `whats_on({ when: "this_weekend" })` resolves the window correctly in `Europe/London` (especially around DST changes)
- `recommend_shows` returns *different* results for different vibes (cosine distance between result sets > threshold is a cheap proxy)
- Invalid params return a clear 400, never a 500
- Empty results return `{ items: [], total: 0 }`, never `null`
- A `slug` lookup is case-insensitive; an `id` lookup is exact

---

## Implementation notes

- The MCP server is a thin wrapper. Each tool maps to one Internal API endpoint. **No business logic in the MCP server itself** — keep it in the API so the website and Custom GPT get the same behaviour.
- Generate the OpenAPI schema from the same source as the MCP tool definitions so the Custom GPT and MCP server stay in sync. A divergence between the two is a category of bug you don't want to hunt.
- Log every tool call with parameters and result count. Aggregate weekly to see what people actually ask for — this is your roadmap for tool refinement.
