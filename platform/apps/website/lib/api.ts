import { NextResponse } from 'next/server';
import { ZodError, type ZodSchema } from 'zod';
import type { ApiError } from '@platform/shared';

/**
 * Parse `Request` body or query params with a zod schema and return either
 * the parsed value or a 400 NextResponse. Keeps every route handler down to
 * about three lines of validation.
 */
export async function parseInput<T>(
  schema: ZodSchema<T>,
  source: Record<string, unknown>,
): Promise<{ ok: true; data: T } | { ok: false; response: NextResponse }> {
  try {
    return { ok: true, data: schema.parse(source) };
  } catch (err) {
    if (err instanceof ZodError) {
      return {
        ok: false,
        response: jsonError(400, 'invalid_input', 'Invalid parameters', {
          issues: err.issues,
        }),
      };
    }
    throw err;
  }
}

export function jsonError(
  status: number,
  code: string,
  message: string,
  details?: Record<string, unknown>,
): NextResponse {
  const body: ApiError = { error: { code, message, details } };
  return NextResponse.json(body, { status });
}

/**
 * Pull URL search params into a plain record, with array support for repeated
 * keys (e.g. `?tags=a&tags=b` → `{ tags: ['a', 'b'] }`).
 */
export function paramsFromUrl(url: URL): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of new Set(url.searchParams.keys())) {
    const all = url.searchParams.getAll(key);
    out[key] = all.length > 1 ? all : coerce(all[0]!);
  }
  return out;
}

function coerce(v: string): unknown {
  if (v === 'true') return true;
  if (v === 'false') return false;
  // Object/array literal — the MCP api-client serialises structured params
  // (e.g. `near: {lat, lng, radius_km}`) as JSON. Decode it back so zod sees
  // the original shape rather than a string.
  if (
    (v.startsWith('{') && v.endsWith('}')) ||
    (v.startsWith('[') && v.endsWith(']'))
  ) {
    try {
      return JSON.parse(v);
    } catch {
      /* fall through to bare-string return */
    }
  }
  if (v !== '' && !Number.isNaN(Number(v))) return Number(v);
  return v;
}
