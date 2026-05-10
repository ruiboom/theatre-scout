import { NextResponse, type NextRequest } from 'next/server';
import { isAdmin } from '@/lib/auth';

export const dynamic = 'force-dynamic';

/**
 * POST /api/v1/admin/refresh — admin-only.
 *
 * Triggers the GitHub Actions "Daily scrape" workflow on `main` via the
 * REST API's `workflow_dispatch` endpoint. Returns 202 if accepted by
 * GitHub, 401/500 otherwise.
 *
 * Required env on the host (set in Vercel):
 *   - GITHUB_TOKEN — fine-grained PAT with `Actions: read & write` for
 *                    ruiboom/theatre-scout
 *   - GITHUB_REPO  — defaults to "ruiboom/theatre-scout"
 *   - GITHUB_WORKFLOW — defaults to "scrape.yml"
 */
export async function POST(req: NextRequest) {
  if (!(await isAdmin())) {
    return NextResponse.json(
      { error: { code: 'forbidden', message: 'Admin only.' } },
      { status: 401 },
    );
  }
  void req;

  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return NextResponse.json(
      {
        error: {
          code: 'misconfigured',
          message:
            'GITHUB_TOKEN env var not set. Create a fine-grained PAT with Actions: read & write on this repo, then add it on Vercel.',
        },
      },
      { status: 500 },
    );
  }

  const repo = process.env.GITHUB_REPO ?? 'ruiboom/theatre-scout';
  const workflow = process.env.GITHUB_WORKFLOW ?? 'scrape.yml';

  const ghUrl = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`;
  const res = await fetch(ghUrl, {
    method: 'POST',
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'x-github-api-version': '2022-11-28',
      'user-agent': 'theatre-scout-admin',
    },
    body: JSON.stringify({ ref: 'main' }),
  });

  if (res.status === 204) {
    return NextResponse.json({ ok: true, dispatched: { repo, workflow, ref: 'main' } });
  }

  const detail = await res.text().catch(() => '');
  return NextResponse.json(
    {
      error: {
        code: 'github_api_error',
        message: `GitHub returned ${res.status} ${res.statusText}`,
        details: { body: detail.slice(0, 500) },
      },
    },
    { status: 502 },
  );
}
