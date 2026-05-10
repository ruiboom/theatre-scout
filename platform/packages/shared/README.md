# @platform/shared

The contract between the Internal API and every surface that consumes it.

## What's here

- **`types.ts`** — TypeScript types matching `docs/TOOL_SURFACE.md` exactly. `Show`, `Venue`, `ShowDetail`, `Recommendation`, plus the envelope shapes for each tool's return.
- **`schemas.ts`** — zod schemas for tool inputs. These are the source of truth for input validation in the API and for MCP tool definitions.

## Why

> *"A `Show` always looks the same regardless of which tool returned it. AIs are unforgiving of inconsistency."* — `TOOL_SURFACE.md`

If types live in one place, the website and MCP server can't drift.

## Usage

```ts
import type { Show, ShowDetail } from '@platform/shared';
import { SearchShowsInput } from '@platform/shared';

const parsed = SearchShowsInput.parse(await req.json());
```
