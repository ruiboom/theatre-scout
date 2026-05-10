/**
 * Single-password admin auth.
 *
 * The password lives in `ADMIN_PASSWORD`. On a successful POST to
 * /admin/login the server sets an HTTP-only cookie whose value is the
 * SHA-256 of the password. Subsequent requests to /admin or
 * /api/v1/admin/* are gated by `requireAdmin()` which re-hashes the env
 * value and compares.
 *
 * This isn't a real auth system — it's a single-user gate for the dashboard.
 * Rotate the password to invalidate all sessions.
 */

import { createHash, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';

const COOKIE = 'ts_admin';
const MAX_AGE_SECONDS = 60 * 60 * 24 * 14; // 14 days

function expectedToken(): string {
  const pw = process.env.ADMIN_PASSWORD;
  if (!pw) {
    throw new Error(
      'ADMIN_PASSWORD env var is not set. The /admin pages need it to gate access.',
    );
  }
  return createHash('sha256').update(pw).digest('hex');
}

/** True if the request bears a valid admin cookie. */
export async function isAdmin(): Promise<boolean> {
  let cookie: string | undefined;
  try {
    cookie = (await cookies()).get(COOKIE)?.value;
  } catch {
    cookie = undefined;
  }
  if (!cookie) return false;
  let want: string;
  try {
    want = expectedToken();
  } catch {
    return false;
  }
  // Constant-time compare to dodge timing oracles.
  const a = Buffer.from(cookie);
  const b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b);
}

/**
 * Validate a candidate password against ADMIN_PASSWORD. Used by the login
 * server action.
 */
export function passwordMatches(candidate: string): boolean {
  const pw = process.env.ADMIN_PASSWORD;
  if (!pw || !candidate) return false;
  const a = Buffer.from(candidate);
  const b = Buffer.from(pw);
  return a.length === b.length && timingSafeEqual(a, b);
}

/** Set the admin cookie. Called from the login server action. */
export async function setAdminCookie(): Promise<void> {
  const jar = await cookies();
  jar.set(COOKIE, expectedToken(), {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: MAX_AGE_SECONDS,
  });
}

/** Clear the admin cookie (logout). */
export async function clearAdminCookie(): Promise<void> {
  const jar = await cookies();
  jar.delete(COOKIE);
}
