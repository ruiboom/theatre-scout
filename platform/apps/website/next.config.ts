import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    typedRoutes: true,
  },
  // The shared package ships TS sources; let Next compile them.
  transpilePackages: ['@platform/shared'],
};

export default config;
