import type { NextConfig } from 'next';

const config: NextConfig = {
  // typedRoutes is appealing but fights any URL built with a dynamic query
  // string (the /shows chip URLs, server-action redirects with error
  // payloads, etc). Off until we want it badly enough to typecast every site.
  // The shared package ships TS sources; let Next compile them.
  transpilePackages: ['@platform/shared'],

  // Bare `/shows` (no filter params) is served by the ISR route
  // `app/shows-index` instead of the per-request dynamic listing. Every filter
  // key the listing reads must be listed here: if any is present the request
  // falls through to the dynamic `app/shows/page.tsx`. Unknown params (utm_*
  // and the like) don't disqualify the rewrite — the listing ignores them, so
  // the cached page is the right answer.
  //
  // Must be `beforeFiles`: `/shows` is itself a filesystem route, and the
  // default (afterFiles) phase only runs once no page has matched — i.e. never,
  // for this URL.
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/shows',
          missing: SHOWS_FILTER_KEYS.map((key) => ({ type: 'query' as const, key })),
          destination: '/shows-index',
        },
      ],
    };
  },
};

const SHOWS_FILTER_KEYS = [
  'q',
  'type',
  'cat',
  'when',
  'date',
  'cal',
  'view',
  'sort',
  'dir',
];

export default config;
