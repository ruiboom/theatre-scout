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
  // Run on everything except Next internals and static assets — no point paying
  // the edge hop for /_next/* or the favicon.
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
