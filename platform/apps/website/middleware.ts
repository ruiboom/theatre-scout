import { NextResponse, type NextRequest } from 'next/server';

/**
 * Edge bot wall.
 *
 * A small, curated set of crawlers that (a) ignore robots.txt and (b) bring us
 * no value — they only burn Neon transfer + compute. They get a 403 at the edge
 * before any page renders or any DB query runs. Everything else passes through:
 * real users, Googlebot/Bingbot (search visibility), and GPTBot/ClaudeBot (the
 * platform deliberately courts AI agents — but via /api/v1 and the MCP server,
 * and those are cached and cheap regardless).
 *
 * Keep this list short and specific. Broad UA matching risks false-positives on
 * real browsers; the softer, broader heuristic that merely *suppresses
 * analytics* lives in `lib/track.ts#isBot`. UA spoofing defeats this — it's a
 * politeness wall against honest-but-greedy bots, not a security boundary.
 */
const BLOCKED_UA =
  /Bytespider|PetalBot|MJ12bot|DotBot|AhrefsBot|SemrushBot|DataForSeoBot|Barkrowler|MauiBot|SeekportBot|serpstatbot|ZoominfoBot|Amazonbot|ImagesiftBot/i;

export function middleware(req: NextRequest) {
  const ua = req.headers.get('user-agent') ?? '';
  if (BLOCKED_UA.test(ua)) {
    return new NextResponse('Forbidden', {
      status: 403,
      headers: { 'x-blocked-by': 'bot-wall' },
    });
  }
  return NextResponse.next();
}

export const config = {
  // Run on pages and the API only — every match is a billed edge invocation,
  // so skip Next internals, robots/sitemap (crawlers we WANT read those), and
  // anything with a file extension (static assets). The eventual replacement
  // is a Vercel Firewall custom rule with the same UA list, which costs
  // nothing per request; see platform/MANAGEMENT_PLAYBOOK.md.
  matcher: [
    '/((?!_next/|favicon\\.ico|robots\\.txt|sitemap\\.xml|.*\\.[a-zA-Z0-9]{2,5}$).*)',
  ],
};
