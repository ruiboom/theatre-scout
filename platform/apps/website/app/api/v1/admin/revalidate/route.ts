import { NextResponse, type NextRequest } from 'next/server';
import { createRemoteJWKSet, jwtVerify } from 'jose';
import { isAdmin } from '@/lib/auth';
import { revalidateSite } from '@/lib/revalidate';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/admin/revalidate — purge the whole site cache.
 *
 * Called by the Daily scrape workflow once the new data is in Neon, so the
 * ISR pages (6 h fallback TTL) and Data Cache entries flip to fresh data
 * within minutes of the scrape instead of drifting for hours.
 *
 * Two ways in:
 *   1. Admin cookie — the dashboard's "Purge page cache" button.
 *   2. A GitHub Actions OIDC token as a bearer. The workflow mints one with
 *      `id-token: write`; we verify it against GitHub's JWKS and require it to
 *      come from THIS repo's `main` branch. No shared secret to provision on
 *      either side — the Vercel deploy and the workflow agree by construction.
 *
 * Purging is harmless in itself (nothing regenerates until requested), but an
 * unauthenticated endpoint would let anyone force the whole site to re-render
 * on demand, which is exactly the cost we're trying to avoid. Hence the gate.
 */

const GITHUB_ISSUER = 'https://token.actions.githubusercontent.com';
const AUDIENCE = 'theatre-scout-revalidate';
const ALLOWED_REPO = process.env.GITHUB_REPO ?? 'ruiboom/theatre-scout';
const ALLOWED_REF = 'refs/heads/main';

const jwks = createRemoteJWKSet(new URL(`${GITHUB_ISSUER}/.well-known/jwks`));

async function isTrustedWorkflow(req: NextRequest): Promise<boolean> {
  const auth = req.headers.get('authorization') ?? '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  if (!token) return false;
  try {
    const { payload } = await jwtVerify(token, jwks, {
      issuer: GITHUB_ISSUER,
      audience: AUDIENCE,
    });
    return payload.repository === ALLOWED_REPO && payload.ref === ALLOWED_REF;
  } catch {
    return false;
  }
}

export async function POST(req: NextRequest) {
  if (!(await isAdmin()) && !(await isTrustedWorkflow(req))) {
    return NextResponse.json(
      { error: { code: 'forbidden', message: 'Admin or trusted workflow only.' } },
      { status: 401 },
    );
  }
  revalidateSite();
  return NextResponse.json({ ok: true, revalidated_at: new Date().toISOString() });
}
