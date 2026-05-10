import postgres from 'postgres';

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set');
}

declare global {
  // eslint-disable-next-line no-var
  var __sql: ReturnType<typeof postgres> | undefined;
}

/**
 * postgres.js singleton.
 *
 * Stashed on `globalThis` so Next.js HMR doesn't open a new pool on every
 * route reload during dev.
 */
export const sql =
  globalThis.__sql ??
  postgres(process.env.DATABASE_URL, {
    max: 10,
    idle_timeout: 20,
    types: {
      // postgres.js parses dates as Date by default — keep them as ISO strings
      // so JSON.stringify is correct without further work.
      date: {
        to: 1184,
        from: [1082, 1083, 1114, 1184],
        serialize: (v: unknown) =>
          v instanceof Date ? v.toISOString() : String(v),
        parse: (v: string) => v,
      },
    },
  });

if (process.env.NODE_ENV !== 'production') {
  globalThis.__sql = sql;
}
