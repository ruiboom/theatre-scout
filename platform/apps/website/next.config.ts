import type { NextConfig } from 'next';

const config: NextConfig = {
  // typedRoutes is appealing but fights any URL built with a dynamic query
  // string (the /shows chip URLs, server-action redirects with error
  // payloads, etc). Off until we want it badly enough to typecast every site.
  // The shared package ships TS sources; let Next compile them.
  transpilePackages: ['@platform/shared'],
};

export default config;
